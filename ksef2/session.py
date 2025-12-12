import logging
import config
import certificate
import auth


_logger = logging.getLogger(__name__)


def create_session():
    """Створює нову KSeF сесію з автентифікацією"""
    # Перевіряємо сертифікати
    public_cert_manager = certificate.PublicCertificateManager(config.api_url)

    if not public_cert_manager.fetch_certificates():
        _logger.error('Failed to fetch public certificates')
        return None

    # Виконуємо автентифікацію
    auth_session = auth.Auth()

    if not auth_session.token:
        _logger.error('Failed to authenticate')
        return None

    _logger.info('Session created successfully')
    return auth_session


# Приклад використання
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = create_session()

    if session and session.token:
        print(f'Session token: {session.token[:50]}...')
    else:
        print('Failed to create session')

