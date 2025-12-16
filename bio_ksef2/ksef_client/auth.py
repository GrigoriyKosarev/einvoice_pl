# -*- coding: utf-8 -*-
"""KSeF Authentication Module - Adapted for Odoo"""
import base64
import time
import dateutil
import logging
import requests

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding as apadding
from cryptography.hazmat.primitives import hashes

from . import certificate as cert


_logger = logging.getLogger(__name__)


class Challenge:
    def __init__(self, api_url):
        self.api_url = api_url
        self.challenge = None
        self.timestamp = None

        try:
            resp = requests.post(f'{self.api_url}/api/v2/auth/challenge', timeout=60)
            if resp.status_code != 200:
                _logger.warning(f'API Error /challenge: {resp.status_code}')
                return

            data = resp.json()
            self.challenge = data.get("challenge")
            self.timestamp = data.get("timestamp")
        except Exception as e:
            _logger.warning(f'API Error /challenge: {e}')


class Auth:
    """Клас для автентифікації в KSeF API"""

    def __init__(self, api_url, ksef_token):
        """
        Ініціалізація та виконання автентифікації

        Args:
            api_url: URL API KSeF (напр. https://ksef-test.mf.gov.pl)
            ksef_token: KSeF токен у форматі: 20251209-EC-...|nip-XXXXXXXXX|...
        """
        self.api_url = api_url
        self.ksef_token = ksef_token
        self.token = None
        self.auth_token = None
        self.reference_number = None
        self.token_valid_until = None
        self.refresh_token = None
        self.refresh_token_valid_until = None

        # Виконуємо автентифікацію
        self._authenticate()

    def _authenticate(self):
        """Виконує повний цикл автентифікації"""
        # 1. Отримуємо challenge
        challenge = Challenge(self.api_url)
        if not challenge.challenge:
            _logger.error('Failed to get challenge')
            return

        # 2. Завантажуємо сертифікат і шифруємо токен
        certificate_obj, public_key = self._load_certificate()
        if not public_key:
            _logger.error('Failed to load certificate')
            return

        dt = dateutil.parser.isoparse(challenge.timestamp)
        t = int(dt.timestamp() * 1000)
        token = f"{self.ksef_token}|{t}".encode('utf-8')

        encrypted_token = public_key.encrypt(
            token,
            apadding.OAEP(
                mgf=apadding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # 3. Формуємо body
        nip = self.ksef_token.split('|')[1].replace('nip-', '')
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
                f'{self.api_url}/api/v2/auth/ksef-token',
                json=body,
                timeout=60
            )
            if resp.status_code != 202:
                _logger.warning(f'API Error /auth/ksef-token: {resp.status_code} - {resp.text}')
                return

            auth_data = resp.json()
            _logger.info(f'Response from /auth/ksef-token: {auth_data}')

            self.auth_token = auth_data.get('authenticationToken', {}).get('token')
            self.reference_number = auth_data.get('referenceNumber')

            if not self.auth_token or not self.reference_number:
                _logger.error('Failed to get auth_token or reference_number from response!')
                return

            _logger.info(f'Authentication initiated, reference: {self.reference_number}')

            # 5. Чекаємо підтвердження
            if not self._wait_for_authentication():
                return

            # 6. Отримуємо фінальний токен
            if not self._redeem_token():
                return

        except Exception as e:
            _logger.error(f'Authentication error: {e}')

    def _wait_for_authentication(self) -> bool:
        """Чекає поки автентифікація буде підтверджена"""
        max_attempts = 30
        attempt = 0

        _logger.info('Starting authentication polling...')

        while attempt < max_attempts:
            attempt += 1
            time.sleep(1)

            try:
                headers = {'Authorization': f'Bearer {self.auth_token}'}
                resp = requests.get(
                    f'{self.api_url}/api/v2/auth/{self.reference_number}',
                    headers=headers,
                    timeout=60
                )

                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get('status', {})
                    code = status.get('code')
                    desc = status.get('description')

                    _logger.info(f'Auth status check #{attempt}: code={code}, desc={desc}')

                    if code == 200:
                        _logger.info('Authentication confirmed! ✓')
                        return True
                    elif code and code >= 300:
                        _logger.error(f'Authentication failed: {desc}')
                        return False
                else:
                    _logger.warning(f'Auth check failed: {resp.status_code}')

            except Exception as e:
                _logger.error(f'Error during auth polling: {e}')
                return False

        _logger.error('Authentication timeout')
        return False

    def _redeem_token(self) -> bool:
        """Обмінює тимчасовий токен на постійний access/refresh токени"""
        try:
            _logger.info('Attempting to redeem token...')

            headers = {'Authorization': f'Bearer {self.auth_token}'}
            resp = requests.post(
                f'{self.api_url}/api/v2/auth/token/redeem',
                headers=headers,
                timeout=60
            )

            if resp.status_code == 200:
                token_data = resp.json()
                _logger.info(f'Response from /auth/token/redeem: {token_data}')

                # Витягуємо accessToken і refreshToken
                self.token = token_data.get('accessToken', {}).get('token')
                self.token_valid_until = token_data.get('accessToken', {}).get('validUntil')
                self.refresh_token = token_data.get('refreshToken', {}).get('token')
                self.refresh_token_valid_until = token_data.get('refreshToken', {}).get('validUntil')

                if self.token:
                    _logger.info(f'✓ Access token obtained')
                    _logger.info(f'  Valid until: {self.token_valid_until}')
                    return True
                else:
                    _logger.error('Failed to extract access token from response')
                    return False
            else:
                _logger.error(f'Token redeem failed: {resp.status_code} - {resp.text}')
                return False

        except Exception as e:
            _logger.error(f'Error redeeming token: {e}')
            return False

    def _load_certificate(self):
        """Завантажує публічний сертифікат для шифрування"""
        try:
            public_cert_manager = cert.PublicCertificateManager(self.api_url)
            if not public_cert_manager.fetch_certificates():
                _logger.error('Failed to fetch certificates')
                return None, None

            cert_data = public_cert_manager.get_ksef_token_cert()
            if not cert_data:
                _logger.error('KsefTokenEncryption certificate not found')
                return None, None

            cert_bytes = base64.b64decode(cert_data)
            certificate = x509.load_der_x509_certificate(cert_bytes)
            public_key = certificate.public_key()

            return certificate, public_key

        except Exception as e:
            _logger.error(f'Error loading certificate: {e}')
            return None, None
