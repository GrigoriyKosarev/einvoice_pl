#!/usr/bin/env python3
"""
Тестовий скрипт для діагностики автентифікації KSeF
"""
import logging
import sys

# Налаштування детального логування
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

import config
import auth

_logger = logging.getLogger(__name__)

def main():
    _logger.info('='*60)
    _logger.info('Starting KSeF Authentication Test')
    _logger.info('='*60)
    _logger.info(f'API URL: {config.api_url}')
    _logger.info(f'KSeF Token: {config.kseftoken[:50]}...')
    _logger.info('='*60)

    # Спроба автентифікації
    try:
        auth_session = auth.Auth()

        if auth_session.token:
            _logger.info('='*60)
            _logger.info('✓ AUTHENTICATION SUCCESSFUL!')
            _logger.info('='*60)
            _logger.info(f'Final token: {auth_session.token[:50]}...')
            _logger.info(f'Session context: {auth_session.session_context}')
            return 0
        else:
            _logger.error('='*60)
            _logger.error('✗ AUTHENTICATION FAILED!')
            _logger.error('='*60)
            return 1

    except Exception as e:
        _logger.error('='*60)
        _logger.error(f'✗ EXCEPTION OCCURRED: {e}')
        _logger.error('='*60)
        import traceback
        traceback.print_exc()
        return 2

if __name__ == '__main__':
    sys.exit(main())
