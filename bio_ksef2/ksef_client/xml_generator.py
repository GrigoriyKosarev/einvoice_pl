# -*- coding: utf-8 -*-
"""Extended Invoice XML Generator for KSeF"""
from datetime import datetime
from typing import List, Dict, Any


def generate_fa_vat_xml(invoice_data: Dict[str, Any], format_version: str = 'FA2') -> str:
    """
    Генерує повноцінний XML інвойсу у форматі FA_VAT для KSeF

    Args:
        invoice_data: Словник з даними інвойсу:
        format_version: Версія формату ('FA2' або 'FA3')
            {
                'invoice_number': str,
                'issue_date': str (YYYY-MM-DD),
                'seller': {
                    'nip': str,
                    'name': str,
                    'street': str,
                    'city': str,
                    'zip': str,
                    'country': str (код країни, напр. 'PL')
                },
                'buyer': {
                    'nip': str,
                    'name': str,
                    'street': str,
                    'city': str,
                    'zip': str,
                    'country': str
                },
                'currency': str (напр. 'PLN'),
                'lines': [
                    {
                        'name': str,           # Назва товару/послуги
                        'quantity': float,     # Кількість
                        'unit': str,          # Одиниця виміру (напр. 'szt', 'kg', 'usł')
                        'price_unit': float,  # Ціна за одиницю без ПДВ
                        'net_amount': float,  # Сума без ПДВ
                        'vat_rate': int,      # Ставка ПДВ %
                        'vat_amount': float,  # Сума ПДВ
                        'gross_amount': float # Сума з ПДВ
                    },
                    ...
                ],
                'total_net': float,       # Загальна сума без ПДВ
                'total_vat': float,       # Загальна сума ПДВ
                'total_gross': float      # Загальна сума з ПДВ
            }

    Returns:
        XML рядок інвойсу FA_VAT
    """

    # DataWytworzeniaFa потребує DateTime
    creation_datetime = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    # Визначаємо параметри формату
    if format_version == 'FA3':
        namespace = 'http://crd.gov.pl/wzor/2023/06/29/12648/'  # FA(3) може мати інший namespace
        kod_systemowy = 'FA (3)'
        wariant = '3'
        wersja_schemy = '1-0E'
    else:  # FA2 за замовчуванням
        namespace = 'http://crd.gov.pl/wzor/2023/06/29/12648/'
        kod_systemowy = 'FA (2)'
        wariant = '2'
        wersja_schemy = '1-0E'

    # Початок XML
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<Faktura xmlns="{namespace}">',
        '    <Naglowek>',
        f'        <KodFormularza kodSystemowy="{kod_systemowy}" wersjaSchemy="{wersja_schemy}">FA</KodFormularza>',
        f'        <WariantFormularza>{wariant}</WariantFormularza>',
        f'        <DataWytworzeniaFa>{creation_datetime}</DataWytworzeniaFa>',
        '        <SystemInfo>Odoo KSeF Integration</SystemInfo>',
        '    </Naglowek>',
    ]

    # Продавець (Podmiot1)
    seller = invoice_data['seller']
    xml_parts.extend([
        '    <Podmiot1>',
        '        <DaneIdentyfikacyjne>',
        f'            <NIP>{_clean_nip(seller["nip"])}</NIP>',
        f'            <Nazwa>{_escape_xml(seller["name"])}</Nazwa>',
        '        </DaneIdentyfikacyjne>',
        '        <Adres>',
        f'            <KodKraju>{seller.get("country", "PL")}</KodKraju>',
        f'            <AdresL1>{_escape_xml(seller.get("street", ""))}</AdresL1>',
        f'            <AdresL2>{seller.get("zip", "")} {_escape_xml(seller.get("city", ""))}</AdresL2>',
        '        </Adres>',
        '    </Podmiot1>',
    ])

    # Покупець (Podmiot2)
    buyer = invoice_data['buyer']
    xml_parts.extend([
        '    <Podmiot2>',
        '        <DaneIdentyfikacyjne>',
        f'            <NIP>{_clean_nip(buyer["nip"])}</NIP>',
        f'            <Nazwa>{_escape_xml(buyer["name"])}</Nazwa>',
        '        </DaneIdentyfikacyjne>',
        '        <Adres>',
        f'            <KodKraju>{buyer.get("country", "PL")}</KodKraju>',
        f'            <AdresL1>{_escape_xml(buyer.get("street", ""))}</AdresL1>',
        f'            <AdresL2>{buyer.get("zip", "")} {_escape_xml(buyer.get("city", ""))}</AdresL2>',
        '        </Adres>',
        '    </Podmiot2>',
    ])

    # Дані факту��и (Fa)
    xml_parts.extend([
        '    <Fa>',
        f'        <KodWaluty>{invoice_data.get("currency", "PLN")}</KodWaluty>',
        f'        <P_1>{invoice_data["issue_date"]}</P_1>',
        f'        <P_2>{_escape_xml(invoice_data["invoice_number"])}</P_2>',
    ])

    # Підсумки за ставками ПДВ
    vat_summary = _calculate_vat_summary(invoice_data['lines'])
    for vat_rate, amounts in vat_summary.items():
        if vat_rate == 23:
            xml_parts.append(f'        <P_13_1>{amounts["net"]:.2f}</P_13_1>')
            xml_parts.append(f'        <P_14_1>{amounts["vat"]:.2f}</P_14_1>')
        elif vat_rate == 8:
            xml_parts.append(f'        <P_13_2>{amounts["net"]:.2f}</P_13_2>')
            xml_parts.append(f'        <P_14_2>{amounts["vat"]:.2f}</P_14_2>')
        elif vat_rate == 5:
            xml_parts.append(f'        <P_13_3>{amounts["net"]:.2f}</P_13_3>')
            xml_parts.append(f'        <P_14_3>{amounts["vat"]:.2f}</P_14_3>')
        elif vat_rate == 0:
            xml_parts.append(f'        <P_13_4>{amounts["net"]:.2f}</P_13_4>')

    # Загальна сума
    xml_parts.append(f'        <P_15>{invoice_data["total_gross"]:.2f}</P_15>')

    # Adnotacje (обов'язкові анотації)
    xml_parts.extend([
        '        <Adnotacje>',
        '            <P_16>2</P_16>',
        '            <P_17>2</P_17>',
        '            <P_18>2</P_18>',
        '            <P_18A>2</P_18A>',
        '            <Zwolnienie>',
        '                <P_19N>1</P_19N>',
        '            </Zwolnienie>',
        '            <NoweSrodkiTransportu>',
        '                <P_22N>1</P_22N>',
        '            </NoweSrodkiTransportu>',
        '            <P_23>2</P_23>',
        '            <PMarzy>',
        '                <P_PMarzyN>1</P_PMarzyN>',
        '            </PMarzy>',
        '        </Adnotacje>',
        '        <RodzajFaktury>VAT</RodzajFaktury>',
    ])

    # Рядки товарів/послуг (FaWiersz)
    for idx, line in enumerate(invoice_data['lines'], start=1):
        xml_parts.extend([
            '        <FaWiersz>',
            f'            <NrWierszaFa>{idx}</NrWierszaFa>',
            f'            <P_7>{_escape_xml(line["name"])}</P_7>',
        ])

        # Додаємо кількість та одиницю якщо є
        if line.get('quantity'):
            xml_parts.append(f'            <P_8A>{line["quantity"]:.2f}</P_8A>')
        if line.get('unit'):
            xml_parts.append(f'            <P_8AJ>{_escape_xml(line["unit"])}</P_8AJ>')

        # Сума без ПДВ
        xml_parts.append(f'            <P_8B>{line["net_amount"]:.2f}</P_8B>')

        # Сума з ПДВ
        xml_parts.append(f'            <P_9A>{line["gross_amount"]:.2f}</P_9A>')

        # Ставка ПДВ
        if line.get('vat_rate') is not None:
            xml_parts.append(f'            <P_11>{line["vat_rate"]}</P_11>')

        # Сума ПДВ
        if line.get('vat_amount'):
            xml_parts.append(f'            <P_12>{line["vat_amount"]:.2f}</P_12>')

        xml_parts.append('        </FaWiersz>')

    # Закриваємо XML
    xml_parts.extend([
        '    </Fa>',
        '</Faktura>',
    ])

    return '\n'.join(xml_parts)


def _clean_nip(nip: str) -> str:
    """Очищає NIP від префіксів та форматування"""
    if not nip:
        return ''
    # Видаляємо PL, pl, пробіли, дефіси
    return nip.replace('PL', '').replace('pl', '').replace(' ', '').replace('-', '').strip()


def _escape_xml(text: str) -> str:
    """Екранує спеціальні символи XML"""
    if not text:
        return ''
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _calculate_vat_summary(lines: List[Dict[str, Any]]) -> Dict[int, Dict[str, float]]:
    """Підраховує підсумки за ставками ПДВ"""
    summary = {}
    for line in lines:
        vat_rate = line.get('vat_rate', 23)
        if vat_rate not in summary:
            summary[vat_rate] = {'net': 0.0, 'vat': 0.0, 'gross': 0.0}

        summary[vat_rate]['net'] += line.get('net_amount', 0.0)
        summary[vat_rate]['vat'] += line.get('vat_amount', 0.0)
        summary[vat_rate]['gross'] += line.get('gross_amount', 0.0)

    return summary
