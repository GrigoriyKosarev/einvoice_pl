import logging
import requests


_logger = logging.getLogger(__name__)

class PublicCertificateManager:

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.certificates = {}
        self.certificates_info = {}

    def fetch_certificates(self) -> bool:
        try:
            resp = requests.get(
                f"{self.api_url}/api/v2/security/public-key-certificates",
                timeout=60
            )

            if resp.status_code != 200:
                _logger.warning(f'API Error /api/v2/security/public-key-certificates: {resp.status_code}')
                return False

            resp_json = resp.json()

            for certificate in resp_json:
                usage = certificate.get("usage", [])
                if not usage or not isinstance(usage, list):
                    continue

                first_usage = usage[0]

                self.certificates[first_usage] = certificate.get("certificate")
                self.certificates_info[first_usage] = {
                    'id': certificate.get('id'),
                    'issuer': certificate.get('issuer'),
                    'valid_to': certificate.get('valid_to'),
                }

            return True

        except Exception as e:
            _logger.error(f'API Upload Error /api/v2/security/public-key-certificates: {e}')
            return False

    def get_ksef_token_cert(self) -> str:
        return self.certificates.get('KsefTokenEncryption')

    def get_symmetric_key_cert(self) -> str:
        return self.certificates.get('SymmetricKeyEncryption')

    def get_invoice_encryption_cert(self) -> str:
        """Отримує сертифікат для шифрування інвойсів"""
        return self.certificates.get('InvoiceEncryption')

    def is_certificate_valid(self, cert_type: str) -> bool:
        return cert_type in self.certificates and self.certificates[cert_type] is not None

    def get_all_usage_types(self) -> list:
        return list(self.certificates.keys())



