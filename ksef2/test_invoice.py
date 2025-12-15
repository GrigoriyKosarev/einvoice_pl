#!/usr/bin/env python3
"""
Тестовий скрипт для перевірки створення та відправки інвойсів
"""
import logging
import sys

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

import config
from session import create_session
from invoice import InvoiceSession, create_sample_invoice_xml

_logger = logging.getLogger(__name__)


def test_invoice_creation():
    """Тест 1: Створення XML інвойсу"""
    _logger.info('='*60)
    _logger.info('TEST 1: Creating sample invoice XML')
    _logger.info('='*60)

    try:
        invoice_xml = create_sample_invoice_xml(
            invoice_number="TEST/2025/001",
            seller_nip="9462527947",
            seller_name="Test Seller Company",
            buyer_nip="1234567890",
            buyer_name="Test Buyer Company",
            net_amount=1000.00,
            vat_rate=23
        )

        _logger.info('✓ Invoice XML created successfully!')
        _logger.info(f'XML length: {len(invoice_xml)} characters')
        _logger.info(f'First 200 chars: {invoice_xml[:200]}...')
        return invoice_xml

    except Exception as e:
        _logger.error(f'✗ Exception: {e}')
        import traceback
        traceback.print_exc()
        return None


def test_invoice_sending(access_token: str, invoice_xml: str):
    """Тест 2: Відправка інвойсу через онлайн сесію"""
    _logger.info('='*60)
    _logger.info('TEST 2: Sending invoice via online session')
    _logger.info('='*60)

    try:
        # Використовуємо context manager для автоматичного відкриття/закриття сесії
        with InvoiceSession(access_token) as inv_session:
            if not inv_session.is_active:
                _logger.error('✗ Failed to open invoice session')
                return False

            # Відправляємо інвойс
            result = inv_session.send_invoice(invoice_xml)

            if result:
                _logger.info('✓ Invoice sent successfully!')
                return True
            else:
                _logger.error('✗ Failed to send invoice')
                return False

    except Exception as e:
        _logger.error(f'✗ Exception: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    _logger.info('='*60)
    _logger.info('KSeF Invoice Creation and Sending Test')
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

    # Тест 1: Створення XML
    invoice_xml = test_invoice_creation()
    results.append(('Invoice XML Creation', invoice_xml is not None))

    if invoice_xml:
        # Тест 2: Відправка інвойсу
        results.append(('Invoice Sending', test_invoice_sending(session.token, invoice_xml)))
    else:
        _logger.error('Skipping invoice sending test due to XML creation failure')
        results.append(('Invoice Sending', False))

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
