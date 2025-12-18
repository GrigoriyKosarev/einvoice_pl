# Джерела інформації про формати XML KSeF

## Офіційна документація KSeF

### 1. Головний портал KSeF
- **URL**: https://www.gov.pl/web/kas/krajowy-system-e-faktur
- **Опис**: Офіційний урядовий сайт з інформацією про Krajowy System e-Faktur
- **Що тут є**: Загальна інформація, новини, дати впровадження, FAQ

### 2. Документація API KSeF
- **URL**: https://ksef.mf.gov.pl/api/
- **Опис**: Технічна документація API KSeF
- **Що тут є**:
  - REST API endpoints
  - Методи аутентифікації
  - Структура запитів та відповідей
  - Коди помилок

### 3. Schema XSD для FA_VAT

#### FA(2) - поточний формат (діє до 31.01.2026)
- **XSD Schema**: http://crd.gov.pl/wzor/2023/06/29/12648/
- **XSD File**: http://crd.gov.pl/xml/schematy/dziedzinowe/mf/2023/06/29/eD/DefinicjeTypy/Schemat.xsd
- **Namespace**: `http://crd.gov.pl/wzor/2023/06/29/12648/`
- **Опис**: XML Schema Definition для формату FA(2)
- **Що тут є**:
  - Структура документу Faktura
  - Обов'язкові та опціональні поля (minOccurs, maxOccurs)
  - Типи даних для кожного поля (TZnakowy, TIlosci, TKwotowy, etc.)
  - Порядок елементів у XML (xsd:sequence)
  - Детальні описи кожного поля у xsd:documentation

#### FA(3) - новий формат (обов'язковий з 01.02.2026)
- **XSD Schema**: http://crd.gov.pl/wzor/2025/01/01/13065/ (очікується)
- **Namespace**: `http://crd.gov.pl/wzor/2025/01/01/13065/` (може бути інший)
- **Опис**: XML Schema Definition для формату FA(3)
- **Статус**: В розробці, очікується оновлення

### 4. Repozytorium GitHub z przykładami
- **URL**: https://github.com/minfinpl/e-faktura
- **Опис**: Офіційне репозиторій Ministerstwa Finansów з прикладами
- **Що тут є**:
  - Приклади XML фактур
  - Приклади коду для інтеграції
  - Тестові випадки

### 5. Centrum Rozliczeń Dokumentów (CRD)
- **URL**: https://www.crd.gov.pl/
- **Опис**: Офіційний портал з wzorami dokumentów
- **Що тут є**:
  - Wzory (шаблони) офіційних документів
  - XSD schemas для різних типів документів
  - Dokumentacja techniczna

## Структура полів FA_VAT

### Основні секції документу

#### 1. Naglowek (Заголовок)
- `KodFormularza` - Код форми документу
  - Атрибут `kodSystemowy`: "FA (2)" або "FA (3)"
  - Атрибут `wersjaSchemy`: версія схеми (наприклад "1-0E")
- `WariantFormularza` - Варіант форми: "2" або "3"
- `DataWytworzeniaFa` - Дата створення (DateTime: YYYY-MM-DDTHH:MM:SS)
- `SystemInfo` - Інформація про систему, що створила документ

#### 2. Podmiot1 (Продавець)
- `DaneIdentyfikacyjne`
  - `NIP` - NIP продавця (10 цифр, без "PL")
  - `Nazwa` - Назва компанії
- `Adres`
  - `KodKraju` - Код країни (PL)
  - `AdresL1` - Адреса рядок 1 (вулиця, номер)
  - `AdresL2` - Адреса рядок 2 (поштовий код, місто)

#### 3. Podmiot2 (Покупець)
- Структура аналогічна Podmiot1

#### 4. Fa (Фактура)

##### Основна інформація:
- `KodWaluty` - Код валюти (PLN, EUR, USD і т.д.)
- `P_1` - Дата виставлення фактури (YYYY-MM-DD)
- `P_2` - Номер фактури
- `P_6` - Дата продажу/виконання послуги (YYYY-MM-DD) **[ОБОВ'ЯЗКОВЕ]**

##### Опціональна секція:
- `WarunkiTransakcji` (може викликати помилки у FA(2))
  - `TerminPlatnosci` - Термін оплати (YYYY-MM-DD, не текст!)

##### Підсумки за ставками ПДВ:
- `P_13_1` - База оподаткування за ставкою 23%
- `P_14_1` - ПДВ за ставкою 23%
- `P_13_2` - База оподаткування за ставкою 8%
- `P_14_2` - ПДВ за ставкою 8%
- `P_13_3` - База оподаткування за ставкою 5%
- `P_14_3` - ПДВ за ставкою 5%
- `P_13_4` - База оподаткування за ставкою 0%
- `P_15` - **Загальна сума з ПДВ** [ОБОВ'ЯЗКОВЕ]

##### Adnotacje (Анотації):
Всі поля приймають значення: "1" (tak) або "2" (nie)
- `P_16` - Marża
- `P_17` - Szczególna procedura (procedura zwolnienia)
- `P_18` - Odwrotne obciążenie
- `P_18A` - Mechanizm podzielonej płatności
- `Zwolnienie/P_19N` - Dostawa towarów/usług zwolnionych
- `NoweSrodkiTransportu/P_22N` - Nowe środki transportu
- `P_23` - Procedura "samofakturowania"
- `PMarzy/P_PMarzyN` - Marża dla biur podróży

##### RodzajFaktury:
- Typ: "VAT", "VAT_RR", "KOREKTA" і т.д.

##### FaWiersz (Рядки товарів/послуг):
**ВАЖЛИВО**: Порядок полів у FaWiersz має бути строгий згідно з офіційним XSD!

- `NrWierszaFa` - Номер рядку (1, 2, 3...) [ОБОВ'ЯЗКОВЕ]
- `P_7` - Назва товару/послуги (type: TZnakowy) [ОПЦІОНАЛЬНЕ для корекції]
  - **Уникайте**: квадратних дужок `[]`, подвійних пробілів, пробілів в кінці
  - **Максимальна довжина**: залежить від версії схеми
- `P_8A` - **Miara** - Одиниця виміру (type: TZnakowy, ТЕКСТ!) [ОПЦІОНАЛЬНЕ]
  - Приклади: "szt", "kg", "usł", "m", "l" **[ТІЛЬКИ ПОЛЬСЬКОЮ МОВОЮ]**
- `P_8B` - **Ilość** - Кількість (type: TIlosci, ЧИСЛО) [ОПЦІОНАЛЬНЕ]
  - Приклад: 10.00
- `P_9A` - **Cena jednostkowa netto** - Ціна за одиницю БЕЗ ПДВ (type: TKwotowy2) [ОПЦІОНАЛЬНЕ]
  - Приклад: 10.00 (за 1 штуку)
- `P_11` - **Wartość sprzedaży netto** - Загальна сума БЕЗ ПДВ (type: TKwotowy) [ОПЦІОНАЛЬНЕ для деяких випадків]
  - Приклад: 100.00 (10 шт × 10.00)
- `P_12` - **Stawka podatku** - Ставка ПДВ у % (type: TStawkaPodatku) [ОПЦІОНАЛЬНЕ]
  - Значення: 23, 8, 5, 0 (без знаку %)

## Типові помилки та їх вирішення

### 1. "Błąd weryfikacji semantyki dokumentu faktury"
**Причини**:
- Відсутнє обов'язкове поле P_6
- Неправильний формат дати (має бути YYYY-MM-DD)
- Текст замість дати в TerminPlatnosci
- Зайві пробіли або спеціальні символи в назвах
- Неправильний порядок елементів у XML
- Одиниці виміру англійською мовою (має бути польською)

**Рішення**:
- Перевірте наявність P_6
- Видаліть WarunkiTransakcji або використовуйте дату, а не текст
- Очистіть назви товарів від подвійних пробілів та дужок
- Використовуйте `product_uom_id.with_context(lang='pl_PL').name` для одиниць виміру

### 2. "Błąd XSD Schema"
**Причини**:
- Неправильний namespace
- Елементи у неправильному порядку
- Неправильний тип даних

**Рішення**:
- Перевірте namespace відповідає версії формату
- Дотримуйтесь порядку елементів відповідно до XSD

### 3. "NIP nieprawidłowy"
**Причини**:
- NIP містить префікс "PL"
- NIP містить дефіси або пробіли

**Рішення**:
- Видаліть "PL" з початку NIP
- Видаліть всі дефіси та пробіли
- NIP має бути 10 цифр

## Корисні інструменти

### 1. Walidator XML online
- **URL**: https://www.freeformatter.com/xml-validator-xsd.html
- **Використання**: Перевірка XML проти XSD schema

### 2. KSeF Test Environment
- **URL**: https://ksef-test.mf.gov.pl
- **Використання**: Тестування інтеграції перед production

### 3. Środowisko testowe API
- **Demo API**: https://ksef-demo.mf.gov.pl/api
- **Документація**: Swagger UI з прикладами запитів

## Приклад правильного XML (FA2)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2023/06/29/12648/">
    <Naglowek>
        <KodFormularza kodSystemowy="FA (2)" wersjaSchemy="1-0E">FA</KodFormularza>
        <WariantFormularza>2</WariantFormularza>
        <DataWytworzeniaFa>2025-12-18T10:00:00</DataWytworzeniaFa>
        <SystemInfo>Odoo KSeF Integration</SystemInfo>
    </Naglowek>
    <Podmiot1>
        <DaneIdentyfikacyjne>
            <NIP>1234567890</NIP>
            <Nazwa>Firma Spółka z o.o.</Nazwa>
        </DaneIdentyfikacyjne>
        <Adres>
            <KodKraju>PL</KodKraju>
            <AdresL1>ul. Testowa 1</AdresL1>
            <AdresL2>00-000 Warszawa</AdresL2>
        </Adres>
    </Podmiot1>
    <Podmiot2>
        <DaneIdentyfikacyjne>
            <NIP>0987654321</NIP>
            <Nazwa>Klient Sp. z o.o.</Nazwa>
        </DaneIdentyfikacyjne>
        <Adres>
            <KodKraju>PL</KodKraju>
            <AdresL1>ul. Krakowska 10</AdresL1>
            <AdresL2>00-001 Kraków</AdresL2>
        </Adres>
    </Podmiot2>
    <Fa>
        <KodWaluty>PLN</KodWaluty>
        <P_1>2025-12-17</P_1>
        <P_2>FV/2025/001</P_2>
        <P_6>2025-12-17</P_6>
        <P_13_1>100.00</P_13_1>
        <P_14_1>23.00</P_14_1>
        <P_15>123.00</P_15>
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
            <P_7>Produkt testowy</P_7>
            <P_8A>szt</P_8A>              <!-- Miara (одиниця виміру, ТЕКСТ) -->
            <P_8B>10.00</P_8B>            <!-- Ilość (кількість, ЧИСЛО) -->
            <P_9A>10.00</P_9A>            <!-- Cena jednostkowa netto (ціна за одиницю без ПДВ) -->
            <P_11>100.00</P_11>           <!-- Wartość sprzedaży netto (загальна сума без ПДВ) -->
            <P_12>23</P_12>               <!-- Stawka podatku (ставка ПДВ %) -->
        </FaWiersz>
    </Fa>
</Faktura>
```

## Різниці між FA(2) та FA(3)

### FA(2) - поточний формат
- **Діє до**: 31 січня 2026
- **Namespace**: `http://crd.gov.pl/wzor/2023/06/29/12648/`
- **kodSystemowy**: "FA (2)"
- **WariantFormularza**: "2"

### FA(3) - новий формат
- **Обов'язковий з**: 1 лютого 2026
- **Namespace**: TBA (буде оголошено)
- **kodSystemowy**: "FA (3)"
- **WariantFormularza**: "3"
- **Зміни**:
  - Можливі нові обов'язкові поля
  - Зміни у структурі Adnotacje
  - Нові типи RodzajFaktury
  - Детальна інформація буде доступна ближче до дати впровадження

## Рекомендації

1. **Завжди тестуйте** на тестовому середовищі перед production
2. **Слідкуйте за оновленнями** на офіційному сайті gov.pl
3. **Зберігайте логи** всіх відправлених XML для debugging
4. **Використовуйте XSD validator** перед відправкою в KSeF
5. **Перевіряйте формат дат** - найпоширеніша помилка
6. **Очищайте текстові поля** від зайвих пробілів та спецсимволів

## Контакти технічної підтримки KSeF

- **Email**: ksef@mf.gov.pl
- **Infolinia**: 22 330 03 30
- **Godziny pracy**: Pon-Pt 8:00-18:00

---

**Останнє оновлення**: 18 грудня 2025
**Версія документу**: 1.0
