import logging
import config
import certificate
import auth


_logger = logging.getLogger(__name__)

public_cert_manager = certificate.PublicCertificateManager(config.api_url)

if public_cert_manager.fetch_certificates():
    # Вибираємо сертифікат KsefTokenEncryption
    cert = public_cert_manager.get_ksef_token_cert()
    challenge = auth.Challenge()


pass

