import base64
import dateutil

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa, padding as apadding
from cryptography.hazmat.primitives import hashes

import config
import certificate as cert
import requests
import logging


_logger = logging.getLogger(__name__)

class Challenge:
    def __init__(self):
        try:
            resp = requests.post(f'{config.api_url}/api/v2/auth/challenge')
            if resp.status_code != 200:
                _logger.warning(f'API Error /challenge: {resp.status_code}')
                return False
            data = resp.json()
            self.challenge = data.get("challenge")
            self.timestamp = data.get("timestamp")
        except Exception as e:
            _logger.warning(f'API Error /challenge: {e}')


class Auth:
    def __init__(self):
        challenge = Challenge()

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

        body = init_token_authentication_request.InitTokenAuthenticationRequest(
            challenge=datachallenge['challenge'],
            context_identifier=authentication_context_identifier.AuthenticationContextIdentifier(
                type_=authentication_context_identifier_type.AuthenticationContextIdentifierType.NIP,
                value=cfg.nip
            ),
            encrypted_token=base64.b64encode(encrypted_token).decode(),
            # authorization_policy=,
        )

        pass

    def loadcertificate(self):
        public_cert_manager = cert.PublicCertificateManager(config.api_url)

        if public_cert_manager.fetch_certificates():
            # Вибираємо сертифікат KsefTokenEncryption
            cert_data = public_cert_manager.get_ksef_token_cert()

            cert_bytes = base64.b64decode(cert_data)
            certificate = x509.load_der_x509_certificate(cert_bytes)
            public_key = certificate.public_key()
            return certificate, public_key



