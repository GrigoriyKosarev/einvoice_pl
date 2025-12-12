import base64
import time
import dateutil
import logging
import requests

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding as apadding
from cryptography.hazmat.primitives import hashes

import config
import certificate as cert


_logger = logging.getLogger(__name__)

class Challenge:
    def __init__(self):
        self.challenge = None
        self.timestamp = None

        try:
            resp = requests.post(f'{config.api_url}/api/v2/auth/challenge')
            if resp.status_code != 200:
                _logger.warning(f'API Error /challenge: {resp.status_code}')
                return

            data = resp.json()
            self.challenge = data.get("challenge")
            self.timestamp = data.get("timestamp")
        except Exception as e:
            _logger.warning(f'API Error /challenge: {e}')


class Auth:
    def __init__(self):
        # 1. Отримуємо challenge
        challenge = Challenge()
        if not challenge.challenge:
            _logger.error('Failed to get challenge')
            self.token = None
            return

        # 2. Завантажуємо сертифікат і шифруємо токен
        certificate, public_key = self.loadcertificate()
        dt = dateutil.parser.isoparse(challenge.timestamp)
        t = int(dt.timestamp() * 1000)
        token = f"{config.kseftoken}|{t}".encode('utf-8')

        encrypted_token = public_key.encrypt(
            token,
            apadding.OAEP(
                mgf=apadding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # 3. Формуємо body як простий словник (без складних класів!)
        nip = config.kseftoken.split('|')[1].replace('nip-', '')  # Витягуємо NIP з токена
        body = {
            "challenge": challenge.challenge,
            "contextIdentifier": {
                "type": "NIP",
                "value": nip
            },
            "encryptedToken": base64.b64encode(encrypted_token).decode()
        }

        # 4. Відправляємо запит на автентифікацію
        try:
            resp = requests.post(
                f'{config.api_url}/api/v2/auth/ksef-token',
                json=body
            )
            if resp.status_code != 202:
                _logger.warning(f'API Error /auth/ksef-token: {resp.status_code} - {resp.text}')
                self.token = None
                return

            auth_data = resp.json()
            _logger.info(f'Step 4 - Response from /auth/ksef-token: {auth_data}')

            # Отримуємо ТИМЧАСОВИЙ токен для перевірки статусу
            self.auth_token = auth_data.get('authenticationToken', {}).get('token')
            self.reference_number = auth_data.get('referenceNumber')

            # Перевіряємо, чи отримали необхідні дані
            if not self.auth_token:
                _logger.error('Failed to get auth_token from response!')
                _logger.error(f'Response structure: {auth_data}')
                self.token = None
                return

            if not self.reference_number:
                _logger.error('Failed to get reference_number from response!')
                _logger.error(f'Response structure: {auth_data}')
                self.token = None
                return

            _logger.info(f'Authentication initiated, reference: {self.reference_number}')
            _logger.info(f'Temporary auth_token: {self.auth_token[:50] if self.auth_token else None}...')

            # 5. Чекаємо підтвердження автентифікації
            if not self._wait_for_authentication():
                self.token = None
                return

            # 6. Отримуємо фінальний токен
            if not self._redeem_token():
                self.token = None
                return

        except Exception as e:
            _logger.error(f'Authentication error: {e}')
            self.token = None

    def _wait_for_authentication(self) -> bool:
        """
        Чекає поки автентифікація буде підтверджена

        Цей метод циклічно перевіряє статус автентифікації.
        Відповідь містить:
        {
            "status": {
                "code": 100-199 (в процесі) / 200 (успіх) / 300+ (помилка),
                "description": "опис статусу"
            },
            "upo": "...",  # якщо є
            "timestamp": "..."
        }
        """
        max_attempts = 30
        attempt = 0

        # Діагностика перед початком
        _logger.info(f'Starting authentication polling...')
        _logger.info(f'Reference number: {self.reference_number}')
        _logger.info(f'Auth token (first 30 chars): {self.auth_token[:30] if self.auth_token else "None"}...')
        _logger.info(f'URL: {config.api_url}/api/v2/auth/{self.reference_number}')

        # ВАЖЛИВО: KSeF API очікує заголовок Authorization з Bearer prefix
        headers = {'Authorization': f'Bearer {self.auth_token}'}

        while attempt < max_attempts:
            try:
                resp = requests.get(
                    f'{config.api_url}/api/v2/auth/{self.reference_number}',
                    headers=headers
                )

                # Обробка різних HTTP статусів
                if resp.status_code == 200:
                    # Успішна відповідь - перевіряємо статус автентифікації
                    data = resp.json()
                    _logger.debug(f'Step 5 - Check status response: {data}')

                    status_code = data.get('status', {}).get('code')
                    status_desc = data.get('status', {}).get('description', 'N/A')

                    _logger.info(f'Auth status check #{attempt + 1}: code={status_code}, desc={status_desc}')

                    if status_code == 200:
                        _logger.info('Authentication confirmed! ✓')
                        return True
                    elif status_code >= 300:
                        _logger.error(f'Authentication failed: {status_desc}')
                        return False

                    # Статус < 200, продовжуємо чекати
                    _logger.info(f'Still processing (code {status_code}), waiting 2 sec...')
                    time.sleep(2)
                    attempt += 1

                elif resp.status_code == 400:
                    # Помилка валідації - виводимо деталі
                    try:
                        error_data = resp.json()
                        _logger.error(f'Validation error (400): {error_data}')
                    except:
                        _logger.error(f'Validation error (400): {resp.text}')
                    return False

                elif resp.status_code == 401:
                    # Не авторизовано - можливо неправильний auth_token
                    _logger.error(f'Unauthorized (401): Invalid or expired auth_token')
                    _logger.debug(f'Auth token used: {self.auth_token[:30] if self.auth_token else None}...')
                    return False

                else:
                    # Інші помилки
                    _logger.warning(f'Unexpected HTTP status {resp.status_code}: {resp.text[:200]}')
                    return False

            except Exception as e:
                _logger.error(f'Error checking auth status: {e}')
                return False

        _logger.error('Authentication timeout')
        return False

    def _redeem_token(self) -> bool:
        """
        Отримує фінальний токен доступу

        Цей метод "викупляє" (redeem) тимчасовий токен на постійний токен сесії.
        Відповідь містить:
        {
            "sessionToken": {
                "token": "фінальний_токен_для_роботи_з_API",
                "context": {...},
                "credentials": {...}
            },
            "referenceNumber": "..."
        }
        """
        try:
            # Діагностика перед запитом
            _logger.info(f'Attempting to redeem token...')
            _logger.info(f'Auth token (first 30 chars): {self.auth_token[:30] if self.auth_token else "None"}...')
            _logger.info(f'URL: {config.api_url}/api/v2/auth/token/redeem')

            # ВАЖЛИВО: KSeF API очікує заголовок Authorization з Bearer prefix
            headers = {'Authorization': f'Bearer {self.auth_token}'}
            resp = requests.post(
                f'{config.api_url}/api/v2/auth/token/redeem',
                headers=headers
            )

            if resp.status_code != 200:
                _logger.error(f'API Error redeeming token: {resp.status_code}')
                try:
                    error_data = resp.json()
                    _logger.error(f'Error details: {error_data}')
                except:
                    _logger.error(f'Error response text: {resp.text}')
                return False

            token_data = resp.json()
            _logger.info(f'Step 6 - Response from /auth/token/redeem: {token_data}')

            # Це вже ФІНАЛЬНИЙ токен для роботи з API!
            self.token = token_data.get('sessionToken', {}).get('token')
            self.session_context = token_data.get('sessionToken', {}).get('context', {})

            _logger.info(f'Final session token obtained: {self.token[:50] if self.token else None}...')
            _logger.info(f'Session context: {self.session_context}')
            return True

        except Exception as e:
            _logger.error(f'Error redeeming token: {e}')
            return False

    def loadcertificate(self):
        public_cert_manager = cert.PublicCertificateManager(config.api_url)

        if public_cert_manager.fetch_certificates():
            # Вибираємо сертифікат KsefTokenEncryption
            cert_data = public_cert_manager.get_ksef_token_cert()

            cert_bytes = base64.b64decode(cert_data)
            certificate = x509.load_der_x509_certificate(cert_bytes)
            public_key = certificate.public_key()
            return certificate, public_key



