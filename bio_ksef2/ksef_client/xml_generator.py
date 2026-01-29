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
                        ⚠️ FA(3) = FA(2) структурно! Обидва генерують kodSystemowy="FA (2)"
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
    buyer_country = buyer.get("country", "PL")
    buyer_nip = buyer.get("nip", "")

    # List of EU countries for VAT-UE format
    eu_countries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']

    xml_parts.extend([
        '    <Podmiot2>',
        '        <DaneIdentyfikacyjne>',
    ])

    # For EU buyers (not Poland), use KodUE + NrVatUE structure
    if buyer_country != 'PL' and buyer_country in eu_countries and buyer_nip:
        # Remove country prefix from VAT number (e.g., LT123456789 -> 123456789)
        clean_vat = _clean_nip(buyer_nip)
        xml_parts.extend([
            f'            <KodUE>{buyer_country}</KodUE>',
            f'            <NrVatUE>{clean_vat}</NrVatUE>',
        ])
    elif buyer_country == 'PL' and buyer_nip:
        # Polish buyer - use NIP
        xml_parts.append(f'            <NIP>{_clean_nip(buyer_nip)}</NIP>')
    elif buyer_nip:
        # Non-EU buyer with tax ID - use KodKraju + NrID
        xml_parts.extend([
            f'            <KodKraju>{buyer_country}</KodKraju>',
            f'            <NrID>{_clean_nip(buyer_nip)}</NrID>',
        ])
    else:
        # No tax ID
        xml_parts.append('            <BrakID>1</BrakID>')

    xml_parts.extend([
        f'            <Nazwa>{_escape_xml(buyer["name"])}</Nazwa>',
        '        </DaneIdentyfikacyjne>',
        '        <Adres>',
        f'            <KodKraju>{buyer_country}</KodKraju>',
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
        # f'        <P_6>{invoice_data["sale_date"]}</P_6>',
        # '         <WarunkiTransakcji>',
        # f'              <TerminPlatnosci>{invoice_data["payment_date"]}</TerminPlatnosci>',
        # '         </WarunkiTransakcji>',
    ])

    # Підсумки за ставками ПДВ
    # IMPORTANT: Amounts in P_13_*, P_14_*, P_15 must be in document currency (e.g., EUR)
    # Only P_14_*W fields contain VAT converted to PLN for foreign currency invoices
    currency_rate = invoice_data.get('currency_rate', 1.0)
    is_foreign_currency = invoice_data.get('is_foreign_currency', False)

    # Determine if this is WDT (intra-EU supply) invoice
    # WDT = buyer from EU (not PL) + 0% VAT rate
    eu_countries = ['AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'NL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE']
    is_wdt = buyer_country != 'PL' and buyer_country in eu_countries

    # Calculate VAT summary in document currency (NO conversion to PLN)
    vat_summary = _calculate_vat_summary(invoice_data['lines'], currency_rate=None)

    for vat_rate, amounts in vat_summary.items():
        if vat_rate == 23:
            xml_parts.append(f'        <P_13_1>{amounts["net"]:.2f}</P_13_1>')
            xml_parts.append(f'        <P_14_1>{amounts["vat"]:.2f}</P_14_1>')
            # P_14_1W - VAT amount converted to PLN (art. 106e ust. 11)
            if is_foreign_currency:
                vat_pln = amounts["vat"] * currency_rate
                xml_parts.append(f'        <P_14_1W>{vat_pln:.2f}</P_14_1W>')
        elif vat_rate == 8:
            xml_parts.append(f'        <P_13_2>{amounts["net"]:.2f}</P_13_2>')
            xml_parts.append(f'        <P_14_2>{amounts["vat"]:.2f}</P_14_2>')
            # P_14_2W - VAT amount converted to PLN (art. 106e ust. 11)
            if is_foreign_currency:
                vat_pln = amounts["vat"] * currency_rate
                xml_parts.append(f'        <P_14_2W>{vat_pln:.2f}</P_14_2W>')
        elif vat_rate == 5:
            xml_parts.append(f'        <P_13_3>{amounts["net"]:.2f}</P_13_3>')
            xml_parts.append(f'        <P_14_3>{amounts["vat"]:.2f}</P_14_3>')
            # P_14_3W - VAT amount converted to PLN (art. 106e ust. 11)
            if is_foreign_currency:
                vat_pln = amounts["vat"] * currency_rate
                xml_parts.append(f'        <P_14_3W>{vat_pln:.2f}</P_14_3W>')
        elif vat_rate == 0:
            # Use P_13_6_2 for WDT (intra-EU supply), P_13_4 for other 0% cases
            # No P_14_* fields for 0% VAT
            if is_wdt:
                xml_parts.append(f'        <P_13_6_2>{amounts["net"]:.2f}</P_13_6_2>')
            else:
                xml_parts.append(f'        <P_13_4>{amounts["net"]:.2f}</P_13_4>')

    # Загальна сума (in document currency, e.g., EUR)
    total_gross = invoice_data['total_gross']
    xml_parts.append(f'        <P_15>{total_gross:.2f}</P_15>')

    # Currency exchange rate (if foreign currency)
    if is_foreign_currency and currency_rate:
        xml_parts.append(f'        <KursWalutyZ>{_format_currency_rate(currency_rate)}</KursWalutyZ>')

    # Adnotacje (обов'язкові анотації)
    xml_parts.extend([
        '        <Adnotacje>',
        '            <P_16>2</P_16>',
        '            <P_17>2</P_17>',
        '            <P_18>2</P_18>',
        '            <P_18A>2</P_18A>',
        '            <Zwolnienie>',
    ])

    # For WDT (intra-EU supply), indicate VAT exemption with legal basis
    if is_wdt:
        xml_parts.extend([
            '                <P_19>1</P_19>',
            '                <P_19A>art. 42 ust. 1 ustawy</P_19A>',
        ])
    else:
        xml_parts.append('                <P_19N>1</P_19N>')

    xml_parts.extend([
        '            </Zwolnienie>',
        '            <NoweSrodkiTransportu>',
        '                <P_22N>1</P_22N>',
        '            </NoweSrodkiTransportu>',
        '            <P_23>2</P_23>',
        '            <PMarzy>',
        '                <P_PMarzyN>1</P_PMarzyN>',
        '            </PMarzy>',
        '        </Adnotacje>',
    ])

    # Determine RodzajFaktury (invoice type)
    rodzaj_faktury = invoice_data.get('rodzaj_faktury', 'VAT')
    xml_parts.append(f'        <RodzajFaktury>{rodzaj_faktury}</RodzajFaktury>')

    # Add credit note specific data (for KOR, KOR_ZAL, KOR_ROZ)
    if rodzaj_faktury in ('KOR', 'KOR_ZAL', 'KOR_ROZ'):
        # PrzyczynaKorekty - reason for correction
        correction_reason = invoice_data.get('correction_reason', '')
        if correction_reason:
            xml_parts.append(f'        <PrzyczynaKorekty>{_escape_xml(correction_reason)}</PrzyczynaKorekty>')

        # TypKorekty - type of correction (1, 2, or 3)
        correction_type = invoice_data.get('correction_type', '2')
        xml_parts.append(f'        <TypKorekty>{correction_type}</TypKorekty>')

        # DaneFaKorygowanej - data of corrected invoice(s)
        # This is REQUIRED for KOR invoices!
        corrected_invoices = invoice_data.get('corrected_invoices', [])
        if not corrected_invoices:
            raise ValueError(
                f'DaneFaKorygowanej is required for invoice type {rodzaj_faktury}. '
                f'corrected_invoices must not be empty!'
            )

        for corrected_inv in corrected_invoices:
            xml_parts.append('        <DaneFaKorygowanej>')
            xml_parts.append(f'            <DataWystFaKorygowanej>{corrected_inv["date"]}</DataWystFaKorygowanej>')
            xml_parts.append(f'            <NrFaKorygowanej>{_escape_xml(corrected_inv["number"])}</NrFaKorygowanej>')

            # Check if original invoice has KSeF number
            ksef_number = corrected_inv.get('ksef_number')
            if ksef_number:
                # Invoice was in KSeF
                xml_parts.append('            <NrKSeF>1</NrKSeF>')
                xml_parts.append(f'            <NrKSeFFaKorygowanej>{ksef_number}</NrKSeFFaKorygowanej>')
            else:
                # Invoice was outside KSeF
                xml_parts.append('            <NrKSeFN>1</NrKSeFN>')

            xml_parts.append('        </DaneFaKorygowanej>')


    # Рядки товарів/послуг (FaWiersz)
    # Згідно з офіційним XSD:
    # P_8A - Miara (одиниця виміру, ТЕКСТ)
    # P_8B - Ilość (кількість, ЧИСЛО)
    # P_9A - Cena jednostkowa netto (ціна за одиницю без ПДВ - оригінальна ціна до знижки)
    # P_10 - Wartość rabatów lub opustów (сума знижки, опціонально)
    # P_11 - Wartość sprzedaży netto (загальна сума після знижки без ПДВ)
    # P_12 - Stawka podatku (ставка ПДВ %)
    for idx, line in enumerate(invoice_data['lines'], start=1):
        xml_parts.extend([
            '        <FaWiersz>',
            f'            <NrWierszaFa>{idx}</NrWierszaFa>',
            f'            <P_7>{_escape_xml(line["name"])}</P_7>',
        ])

        # Indeks - Internal product code/SKU
        if line.get('index'):
            xml_parts.append(f'            <Indeks>{_escape_xml(line["index"])}</Indeks>')

        # GTIN - Product barcode (cleaned from trailing special chars)
        if line.get('gtin'):
            xml_parts.append(f'            <GTIN>{_escape_xml(line["gtin"])}</GTIN>')

        # P_8A - Miara (одиниця виміру)
        if line.get('unit'):
            xml_parts.append(f'            <P_8A>{_escape_xml(line["unit"])}</P_8A>')

        # P_8B - Ilość (кількість)
        if line.get('quantity'):
            xml_parts.append(f'            <P_8B>{line["quantity"]:.2f}</P_8B>')

        # P_9A - Cena jednostkowa netto (ціна за одиницю без ПДВ - оригінальна ціна)
        if line.get('price_unit') is not None:
            xml_parts.append(f'            <P_9A>{line["price_unit"]:.2f}</P_9A>')

        # P_10 - Wartość rabatów lub opustów (сума знижок)
        if line.get('discount_amount') and line['discount_amount'] > 0:
            xml_parts.append(f'            <P_10>{line["discount_amount"]:.2f}</P_10>')

        # P_11 - Wartość sprzedaży netto (загальна сума після знижки без ПДВ)
        xml_parts.append(f'            <P_11>{line["net_amount"]:.2f}</P_11>')

        # P_12 - Stawka podatku (ставка ПДВ %)
        if line.get('vat_rate') is not None:
            xml_parts.append(f'            <P_12>{line["vat_rate"]}</P_12>')

        # Procedura - Special procedures (optional)
        # NOTE: WDT (intra-EU supply) does NOT use Procedura field
        # Valid values: WSTO_EE, IED, TT_D, I_42, I_63, B_SPV, B_SPV_DOSTAWA, B_MPV_PROWIZJA
        # IMPORTANT: Must come BEFORE KursWaluty according to XSD sequence
        if line.get('procedure'):
            xml_parts.append(f'            <Procedura>{line["procedure"]}</Procedura>')

        # KursWaluty - Курс валюти (для іноземної валюти)
        # IMPORTANT: Must come AFTER Procedura according to XSD sequence
        if line.get('currency_rate'):
            xml_parts.append(f'            <KursWaluty>{_format_currency_rate(line["currency_rate"])}</KursWaluty>')

        # DodatkowyOpis - Customer-specific product information
        # IMPORTANT: Must be at the END of FaWiersz element, after all other fields
        if line.get('customer_product_code'):
            xml_parts.extend([
                '            <DodatkowyOpis>',
                '                <Klucz>CustomerProductCode</Klucz>',
                f'                <Wartosc>{_escape_xml(line["customer_product_code"])}</Wartosc>',
                '            </DodatkowyOpis>',
            ])
        if line.get('customer_product_name'):
            xml_parts.extend([
                '            <DodatkowyOpis>',
                '                <Klucz>CustomerProductName</Klucz>',
                f'                <Wartosc>{_escape_xml(line["customer_product_name"])}</Wartosc>',
                '            </DodatkowyOpis>',
            ])

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


def _format_currency_rate(rate: float) -> str:
    """
    Форматує курс валюти згідно з XSD вимогами для TIlosci

    TIlosci дозволяє максимум 6 знаків після коми
    Pattern: -?([1-9]\d{0,15}|0)(\.\d{1,6})?
    """
    # Format with 6 decimal places max
    formatted = f'{rate:.6f}'
    # Remove trailing zeros and decimal point if not needed
    formatted = formatted.rstrip('0').rstrip('.')
    return formatted


def _escape_xml(text: str) -> str:
    """Екранує спеціальні символи XML"""
    if not text:
        return ''

    import re
    text = re.sub(r'\s+', ' ', text).strip()

    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _calculate_vat_summary(lines: List[Dict[str, Any]], currency_rate: float = None) -> Dict[int, Dict[str, float]]:
    """
    Підраховує підсумки за ставками ПДВ в валюті документа

    Args:
        lines: Рядки інвойсу
        currency_rate: DEPRECATED - не використовується (суми завжди в валюті документа)

    Returns:
        Dict з підсумками за ставками ПДВ в валюті документа
    """
    summary = {}
    for line in lines:
        vat_rate = line.get('vat_rate', 23)
        if vat_rate not in summary:
            summary[vat_rate] = {'net': 0.0, 'vat': 0.0, 'gross': 0.0}

        # NO currency conversion - amounts stay in document currency (e.g., EUR)
        # Conversion to PLN only happens for P_14_*W fields in the main XML generation
        summary[vat_rate]['net'] += line.get('net_amount', 0.0)
        summary[vat_rate]['vat'] += line.get('vat_amount', 0.0)
        summary[vat_rate]['gross'] += line.get('gross_amount', 0.0)

    return summary
