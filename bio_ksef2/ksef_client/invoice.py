#!/usr/bin/env python3
"""
Модуль для роботи з інвойсами KSeF (створення, відправка, перевірка)
"""
import logging
import requests
import base64
import os
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as apadding
from cryptography.hazmat.primitives import hashes
from cryptography import x509

# config removed
from . import certificate as cert

_logger = logging.getLogger(__name__)


class InvoiceSession:
    """Клас для роботи з онлайн сесією відправки інвойсів"""

    def __init__(self, api_url: str, access_token: str):
        """
        Ініціалізація сесії відправки інвойсів

        Args:
            api_url: URL API KSeF
            access_token: Access token отриманий після автентифікації
        """
        self.api_url = api_url
        self.access_token = access_token
        self.session_reference = None
        self.is_active = False
        self.aes_key = None  # Симетричний ключ AES для шифрування
        self.iv = None  # Вектор ініціалізації

    def open(self) -> bool:
        """
        Відкриває онлайн сесію для відправки інвойсів

        Returns:
            True якщо сесія успішно відкрита, False інакше
        """
        try:
            # 1. Генеруємо випадковий 32-байтний AES ключ і 16-байтний IV
            self.aes_key = os.urandom(32)  # 256 біт для AES-256
            self.iv = os.urandom(16)  # 128 біт для AES block size

            # 2. Отримуємо публічний сертифікат для шифрування
            public_cert_manager = cert.PublicCertificateManager(self.api_url)
            if not public_cert_manager.fetch_certificates():
                _logger.error('Failed to fetch public certificates')
                return False

            # Використовуємо сертифікат SymmetricKeyEncryption
            cert_data = public_cert_manager.get_symmetric_key_cert()
            cert_bytes = base64.b64decode(cert_data)
            certificate = x509.load_der_x509_certificate(cert_bytes)
            public_key = certificate.public_key()

            # 3. Шифруємо AES ключ за допомогою RSA-OAEP
            encrypted_aes_key = public_key.encrypt(
                self.aes_key,
                apadding.OAEP(
                    mgf=apadding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )

            # 4. Формуємо body запиту
            body = {
                "formCode": {
                    "systemCode": "FA (2)",
                    "schemaVersion": "1-0E",
                    "value": "FA"
                },
                "encryption": {
                    "encryptedSymmetricKey": base64.b64encode(encrypted_aes_key).decode('utf-8'),
                    "initializationVector": base64.b64encode(self.iv).decode('utf-8')
                }
            }

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            resp = requests.post(
                f'{self.api_url}/api/v2/sessions/online',
                headers=headers,
                json=body
            )

            if resp.status_code == 201:
                data = resp.json()
                self.session_reference = data.get('referenceNumber') or data.get('sessionReferenceNumber')
                self.is_active = True
                _logger.info(f'✓ Online session opened: {self.session_reference}')
                return True
            else:
                _logger.error(f'Failed to open session: {resp.status_code}')
                try:
                    error_data = resp.json()
                    _logger.error(f'Error details: {error_data}')
                except:
                    _logger.error(f'Response: {resp.text}')
                return False

        except Exception as e:
            _logger.error(f'Exception opening session: {e}')
            import traceback
            traceback.print_exc()
            return False

    def send_invoice(self, invoice_xml: str) -> Optional[Dict[str, Any]]:
        """
        Відправляє інвойс в онлайн сесію

        Args:
            invoice_xml: XML інвойсу в форматі FA_VAT

        Returns:
            Словник з даними відповіді або None у випадку помилки
        """
        if not self.is_active:
            _logger.error('Session is not active! Call open() first.')
            return None

        try:
            # 1. Підготовка даних
            invoice_bytes = invoice_xml.encode('utf-8')
            invoice_size = len(invoice_bytes)

            # 2. Хеш оригінального інвойсу (SHA-256)
            invoice_hash = hashlib.sha256(invoice_bytes).digest()
            invoice_hash_b64 = base64.b64encode(invoice_hash).decode('utf-8')

            # 3. Шифрування інвойсу за допомогою AES-256-CBC з PKCS#7 padding
            padder = sym_padding.PKCS7(128).padder()  # 128 біт для AES block size
            padded_data = padder.update(invoice_bytes) + padder.finalize()

            cipher = Cipher(algorithms.AES(self.aes_key), modes.CBC(self.iv))
            encryptor = cipher.encryptor()
            encrypted_invoice = encryptor.update(padded_data) + encryptor.finalize()

            # 4. Хеш і розмір зашифрованого інвойсу
            encrypted_invoice_size = len(encrypted_invoice)
            encrypted_invoice_hash = hashlib.sha256(encrypted_invoice).digest()
            encrypted_invoice_hash_b64 = base64.b64encode(encrypted_invoice_hash).decode('utf-8')
            encrypted_invoice_b64 = base64.b64encode(encrypted_invoice).decode('utf-8')

            # 5. Формуємо body запиту
            body = {
                "invoiceHash": invoice_hash_b64,
                "invoiceSize": invoice_size,
                "encryptedInvoiceHash": encrypted_invoice_hash_b64,
                "encryptedInvoiceSize": encrypted_invoice_size,
                "encryptedInvoiceContent": encrypted_invoice_b64
            }

            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            resp = requests.post(
                f'{self.api_url}/api/v2/sessions/online/{self.session_reference}/invoices',
                headers=headers,
                json=body
            )

            if resp.status_code == 202:
                data = resp.json()
                _logger.info(f'✓ Invoice sent successfully')
                ref_num = data.get("referenceNumber") or data.get("invoiceReferenceNumber")
                proc_code = data.get("processingCode")
                if ref_num:
                    _logger.info(f'  Reference: {ref_num}')
                if proc_code:
                    _logger.info(f'  Processing code: {proc_code}')
                return data
            else:
                _logger.error(f'Failed to send invoice: {resp.status_code}')
                try:
                    error_data = resp.json()
                    _logger.error(f'Error details: {error_data}')
                except:
                    _logger.error(f'Response: {resp.text}')
                return None

        except Exception as e:
            _logger.error(f'Exception sending invoice: {e}')
            import traceback
            traceback.print_exc()
            return None

    def get_invoice_status(self, invoice_reference_number: str) -> Optional[Dict[str, Any]]:
        """
        Перевіряє статус відправленого інвойсу

        Args:
            invoice_reference_number: Референс-номер інвойсу, отриманий після відправки

        Returns:
            Словник з даними статусу або None у випадку помилки
        """
        if not self.is_active:
            _logger.error('Session is not active!')
            return None

        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }

            resp = requests.get(
                f'{self.api_url}/api/v2/sessions/{self.session_reference}/invoices/{invoice_reference_number}',
                headers=headers
            )

            if resp.status_code == 200:
                data = resp.json()
                _logger.info(f'Invoice status retrieved successfully')

                status = data.get("status", {})
                status_code = status.get("code")
                status_desc = status.get("description")
                status_details = status.get("details", [])

                _logger.info(f'  Status code: {status_code}')
                _logger.info(f'  Status description: {status_desc}')
                if status_details:
                    _logger.info(f'  Status details:')
                    for detail in status_details:
                        _logger.info(f'    - {detail}')

                _logger.info(f'  KSeF number: {data.get("ksefNumber")}')
                return data
            else:
                _logger.error(f'Failed to get invoice status: {resp.status_code}')
                try:
                    error_data = resp.json()
                    _logger.error(f'Error details: {error_data}')
                except:
                    _logger.error(f'Response: {resp.text}')
                return None

        except Exception as e:
            _logger.error(f'Exception getting invoice status: {e}')
            import traceback
            traceback.print_exc()
            return None

    def close(self) -> bool:
        """
        Закриває онлайн сесію

        Returns:
            True якщо сесія успішно закрита, False інакше
        """
        if not self.is_active:
            _logger.warning('Session is not active')
            return True

        try:
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }

            body = {}

            resp = requests.post(
                f'{self.api_url}/api/v2/sessions/online/{self.session_reference}/close',
                headers=headers,
                json=body
            )

            if resp.status_code in (200, 204):
                self.is_active = False
                _logger.info(f'✓ Session closed successfully')
                if resp.status_code == 200 and resp.text:
                    data = resp.json()
                    proc_code = data.get("processingCode")
                    proc_desc = data.get("processingDescription")
                    if proc_code:
                        _logger.info(f'  Processing code: {proc_code}')
                    if proc_desc:
                        _logger.info(f'  Processing description: {proc_desc}')
                return True
            else:
                _logger.error(f'Failed to close session: {resp.status_code}')
                try:
                    error_data = resp.json()
                    _logger.error(f'Error details: {error_data}')
                except:
                    _logger.error(f'Response: {resp.text}')
                return False

        except Exception as e:
            _logger.error(f'Exception closing session: {e}')
            return False

    def __enter__(self):
        """Context manager enter"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if self.is_active:
            self.close()


def create_sample_invoice_xml(
    invoice_number: str,
    seller_nip: str,
    seller_name: str,
    buyer_nip: str,
    buyer_name: str,
    net_amount: float,
    gross_amount: float,
    vat_amount: float,
    vat_rate: int = 23,
    issue_date: Optional[str] = None
) -> str:
    """
    Створює простий XML інвойсу FA_VAT

    Args:
        invoice_number: Номер інвойсу
        seller_nip: NIP продавця
        seller_name: Назва продавця
        buyer_nip: NIP покупця
        buyer_name: Назва покупця
        net_amount: Сума нетто
        vat_rate: Ставка ПДВ (23 за замовчуванням)
        issue_date: Дата виставлення (YYYY-MM-DD), за замовчуванням сьогодні

    Returns:
        XML рядок інвойсу
    """
    if issue_date is None:
        issue_date = datetime.now().strftime('%Y-%m-%d')

    # DataWytworzeniaFa потребує повний DateTime з часом
    creation_datetime = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # vat_amount = round(net_amount * vat_rate / 100, 2)
    # gross_amount = round(net_amount + vat_amount, 2)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2023/06/29/12648/">
    <Naglowek>
        <KodFormularza kodSystemowy="FA (2)" wersjaSchemy="1-0E">FA</KodFormularza>
        <WariantFormularza>2</WariantFormularza>
        <DataWytworzeniaFa>{creation_datetime}</DataWytworzeniaFa>
        <SystemInfo>KSeF Python Client</SystemInfo>
    </Naglowek>
    <Podmiot1>
        <DaneIdentyfikacyjne>
            <NIP>{seller_nip}</NIP>
            <Nazwa>{seller_name}</Nazwa>
        </DaneIdentyfikacyjne>
        <Adres>
            <KodKraju>PL</KodKraju>
            <AdresL1>Test Address 1</AdresL1>
            <AdresL2>00-000 Warszawa</AdresL2>
        </Adres>
    </Podmiot1>
    <Podmiot2>
        <DaneIdentyfikacyjne>
            <NIP>{buyer_nip}</NIP>
            <Nazwa>{buyer_name}</Nazwa>
        </DaneIdentyfikacyjne>
        <Adres>
            <KodKraju>PL</KodKraju>
            <AdresL1>Buyer Address 1</AdresL1>
            <AdresL2>00-000 Warszawa</AdresL2>
        </Adres>
    </Podmiot2>
    <Fa>
        <KodWaluty>PLN</KodWaluty>
        <P_1>{issue_date}</P_1>
        <P_2>{invoice_number}</P_2>
        <P_13_1>{net_amount:.2f}</P_13_1>
        <P_14_1>{vat_amount:.2f}</P_14_1>
        <P_15>{gross_amount:.2f}</P_15>
        <Adnotacje>
            <P_16>2</P_16>
            <P_17>2</P_17>
            <P_18>2</P_18>
            <P_18A>2</P_18A>
            <Zwolnienie>
                <P_19N>1</P_19N>
            </Zwolnienie>
            <NoweSrodkiTransportu>
                <P_22N>1</P_22N>
            </NoweSrodkiTransportu>
            <P_23>2</P_23>
            <PMarzy>
                <P_PMarzyN>1</P_PMarzyN>
            </PMarzy>
        </Adnotacje>
        <RodzajFaktury>VAT</RodzajFaktury>
        <FaWiersz>
            <NrWierszaFa>1</NrWierszaFa>
            <P_7>Test product/service</P_7>
            <P_8B>{net_amount:.2f}</P_8B>
            <P_9A>{gross_amount:.2f}</P_9A>
        </FaWiersz>
    </Fa>
</Faktura>"""

    return xml
