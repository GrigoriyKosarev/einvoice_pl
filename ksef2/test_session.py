#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки роботи з KSeF API після автентифікації
"""
import logging
import sys
import requests

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

import config
from session import create_session

_logger = logging.getLogger(__name__)


def test_session_status(session):
    """Тест 1: Перевірка статусу сесії"""
    _logger.info('='*60)
    _logger.info('TEST 1: Checking session status')
    _logger.info('='*60)

    try:
        headers = {'Authorization': f'Bearer {session.token}'}
        resp = requests.get(
            f'{config.api_url}/api/v2/session/status',
            headers=headers
        )

        if resp.status_code == 200:
            data = resp.json()
            _logger.info('✓ Session status retrieved successfully!')
            _logger.info(f'Session active: {data.get("active", "N/A")}')
            _logger.info(f'Context: {data.get("context", {})}')
            return True
        else:
            _logger.error(f'✗ Failed to get session status: {resp.status_code}')
            _logger.error(f'Response: {resp.text}')
            return False

    except Exception as e:
        _logger.error(f'✗ Exception: {e}')
        return False


def test_token_info(session):
    """Тест 2: Інформація про токен"""
    _logger.info('='*60)
    _logger.info('TEST 2: Token information')
    _logger.info('='*60)

    _logger.info(f'Access Token: {session.token[:50]}...')
    _logger.info(f'  Valid until: {session.token_valid_until}')
    _logger.info(f'Refresh Token: {session.refresh_token[:50]}...')
    _logger.info(f'  Valid until: {session.refresh_token_valid_until}')
    return True


def test_credentials_list(session):
    """Тест 3: Список credentials (токенів/ключів)"""
    _logger.info('='*60)
    _logger.info('TEST 3: Listing credentials')
    _logger.info('='*60)

    try:
        headers = {'Authorization': f'Bearer {session.token}'}
        resp = requests.get(
            f'{config.api_url}/api/v2/credentials',
            headers=headers
        )

        if resp.status_code == 200:
            data = resp.json()
            _logger.info('✓ Credentials list retrieved successfully!')
            credentials = data.get('credentialsList', [])
            _logger.info(f'Total credentials: {len(credentials)}')

            for i, cred in enumerate(credentials, 1):
                _logger.info(f'\nCredential #{i}:')
                _logger.info(f'  Identifier: {cred.get("identifier", "N/A")}')
                _logger.info(f'  Type: {cred.get("type", "N/A")}')
                _logger.info(f'  Status: {cred.get("status", "N/A")}')
                _logger.info(f'  Valid from: {cred.get("validFrom", "N/A")}')
                _logger.info(f'  Valid to: {cred.get("validTo", "N/A")}')

            return True
        else:
            _logger.warning(f'Failed to get credentials: {resp.status_code}')
            _logger.warning(f'Response: {resp.text}')
            return False

    except Exception as e:
        _logger.error(f'✗ Exception: {e}')
        return False


def test_invoice_query(session):
    """Тест 4: Запит на пошук рахунків (може бути порожній список)"""
    _logger.info('='*60)
    _logger.info('TEST 4: Querying invoices')
    _logger.info('='*60)

    try:
        headers = {
            'Authorization': f'Bearer {session.token}',
            'Content-Type': 'application/json'
        }

        # Запит на пошук рахунків за останні 7 днів
        from datetime import datetime, timedelta
        date_to = datetime.now()
        date_from = date_to - timedelta(days=7)

        body = {
            "queryCriteria": {
                "subjectType": "subject1",
                "type": "range",
                "invoicingDateFrom": date_from.strftime('%Y-%m-%d'),
                "invoicingDateTo": date_to.strftime('%Y-%m-%d')
            }
        }

        resp = requests.post(
            f'{config.api_url}/api/v2/query/invoice/sync',
            headers=headers,
            json=body
        )

        if resp.status_code == 200:
            data = resp.json()
            _logger.info('✓ Invoice query executed successfully!')
            invoices = data.get('invoiceHeaderList', [])
            _logger.info(f'Found {len(invoices)} invoices')

            if invoices:
                for i, inv in enumerate(invoices[:3], 1):  # Показуємо перші 3
                    _logger.info(f'\nInvoice #{i}:')
                    _logger.info(f'  Number: {inv.get("invoiceNumber", "N/A")}')
                    _logger.info(f'  Date: {inv.get("invoicingDate", "N/A")}')
                    _logger.info(f'  Amount: {inv.get("amount", "N/A")}')

            return True
        else:
            _logger.warning(f'Invoice query failed: {resp.status_code}')
            _logger.warning(f'Response: {resp.text}')
            return False

    except Exception as e:
        _logger.error(f'✗ Exception: {e}')
        return False


def main():
    _logger.info('='*60)
    _logger.info('KSeF API Session Testing')
    _logger.info('='*60)

    # Створюємо сесію
    _logger.info('Creating authenticated session...')
    session = create_session()

    if not session or not session.token:
        _logger.error('Failed to create session! Exiting.')
        return 1

    _logger.info('✓ Session created successfully!\n')

    # Запускаємо тести
    results = []

    results.append(('Token Info', test_token_info(session)))
    results.append(('Session Status', test_session_status(session)))
    results.append(('Credentials List', test_credentials_list(session)))
    results.append(('Invoice Query', test_invoice_query(session)))

    # Підсумок
    _logger.info('\n' + '='*60)
    _logger.info('TEST SUMMARY')
    _logger.info('='*60)

    for test_name, result in results:
        status = '✓ PASSED' if result else '✗ FAILED'
        _logger.info(f'{test_name}: {status}')

    passed = sum(1 for _, r in results if r)
    total = len(results)

    _logger.info('='*60)
    _logger.info(f'Total: {passed}/{total} tests passed')
    _logger.info('='*60)

    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())
