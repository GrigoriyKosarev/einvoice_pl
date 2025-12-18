# FA_VAT XML Fields Reference

Довідник полів XML інвойсу у форматі FA_VAT для KSeF.

## Офіційні джерела документації:

- **KSeF База знань**: https://ksef.podatki.gov.pl/baza-wiedzy-ksef/pliki-do-pobrania-ksef/
- **Структура FA**: https://ksef.podatki.gov.pl/informacje-ogolne-ksef-20/faktura-ustrukturyzowana-i-struktura-logiczna-fa/
- **Struktury XML**: https://www.podatki.gov.pl/e-deklaracje/dokumentacja-it/struktury-dokumentow-xml/#ksef

## Версії структури:

- **FA(2)** - діє до 31.01.2026 (поточна версія)
- **FA(3)** - обов'язкова з 01.02.2026

## Основна структура XML:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2023/06/29/12648/">
    <Naglowek>...</Naglowek>
    <Podmiot1>...</Podmiot1>  <!-- Продавець -->
    <Podmiot2>...</Podmiot2>  <!-- Покупець -->
    <Fa>...</Fa>              <!-- Дані інвойсу -->
</Faktura>
```

---

## 1. Naglowek (Заголовок)

```xml
<Naglowek>
    <KodFormularza kodSystemowy="FA (2)" wersjaSchemy="1-0E">FA</KodFormularza>
    <WariantFormularza>2</WariantFormularza>
    <DataWytworzeniaFa>2025-12-16T10:30:00</DataWytworzeniaFa>  <!-- DateTime! -->
    <SystemInfo>Nazwa systemu</SystemInfo>
</Naglowek>
```

### Поля:
- **KodFormularza**: Код формуляра (FA)
- **WariantFormularza**: Варіант (2 = FA(2))
- **DataWytworzeniaFa**: ⚠️ **DateTime** створення (не тільки дата!)
- **SystemInfo**: Назва системи (необов'язково)

---

## 2. Podmiot1 (Продавець)

```xml
<Podmiot1>
    <DaneIdentyfikacyjne>
        <NIP>9462527947</NIP>
        <Nazwa>Nazwa firmy</Nazwa>
    </DaneIdentyfikacyjne>
    <Adres>
        <KodKraju>PL</KodKraju>
        <AdresL1>ul. Testowa 1</AdresL1>
        <AdresL2>00-000 Warszawa</AdresL2>
    </Adres>
</Podmiot1>
```

### Поля:
- **NIP**: NIP продавця (без префіксу PL)
- **Nazwa**: Назва компанії
- **KodKraju**: Код країни (PL)
- **AdresL1**: Вулиця та номер будинку
- **AdresL2**: Поштовий індекс та місто

---

## 3. Podmiot2 (Покупець)

Аналогічна структура як Podmiot1.

---

## 4. Fa (Дані інвойсу)

### 4.1 Основні дані:

```xml
<Fa>
    <KodWaluty>PLN</KodWaluty>
    <P_1>2025-12-16</P_1>              <!-- Дата виставлення -->
    <P_2>INV/2025/001</P_2>            <!-- Номер інвойсу -->
```

### 4.2 Підсумки за ставками ПДВ:

```xml
    <!-- 23% ПДВ -->
    <P_13_1>1000.00</P_13_1>           <!-- Wartość netto 23% -->
    <P_14_1>230.00</P_14_1>            <!-- Kwota VAT 23% -->

    <!-- 8% ПДВ -->
    <P_13_2>500.00</P_13_2>            <!-- Wartość netto 8% -->
    <P_14_2>40.00</P_14_2>             <!-- Kwota VAT 8% -->

    <!-- 5% ПДВ -->
    <P_13_3>200.00</P_13_3>            <!-- Wartość netto 5% -->
    <P_14_3>10.00</P_14_3>             <!-- Kwota VAT 5% -->

    <!-- 0% / zwolnione -->
    <P_13_4>100.00</P_13_4>            <!-- Wartość netto 0% -->

    <!-- Загальна сума -->
    <P_15>2080.00</P_15>               <!-- Suma brutto -->
```

#### Пояснення полів P_13 і P_14:

| Поле | Опис | Ставка ПДВ |
|------|------|------------|
| P_13_1 | Сума без ПДВ (netto) | 23% |
| P_14_1 | Сума ПДВ | 23% |
| P_13_2 | Сума без ПДВ (netto) | 8% |
| P_14_2 | Сума ПДВ | 8% |
| P_13_3 | Сума без ПДВ (netto) | 5% |
| P_14_3 | Сума ПДВ | 5% |
| P_13_4 | Сума без ПДВ (netto) | 0% / zwolnione |
| P_15 | **Загальна сума з ПДВ (brutto)** | - |

### 4.3 Adnotacje (Анотації):

```xml
    <Adnotacje>
        <P_16>2</P_16>          <!-- Faktura nie dotyczy procedury marży -->
        <P_17>2</P_17>          <!-- Nie dotyczy dostawy towarów używanych -->
        <P_18>2</P_18>          <!-- Nie dotyczy dostawy dzieł sztuki -->
        <P_18A>2</P_18A>        <!-- Nie dotyczy antyków lub przedmiotów kolekcjonerskich -->
        <Zwolnienie>
            <P_19N>1</P_19N>    <!-- Brak zwolnień podatkowych -->
        </Zwolnienie>
        <NoweSrodkiTransportu>
            <P_22N>1</P_22N>    <!-- Nie dotyczy nowych środków transportu -->
        </NoweSrodkiTransportu>
        <P_23>2</P_23>          <!-- Nie dotyczy procedur szczególnych -->
        <PMarzy>
            <P_PMarzyN>1</P_PMarzyN>  <!-- Brak procedury marży -->
        </PMarzy>
    </Adnotacje>
```

**Важливо:** Ці анотації обов'язкові! Значення:
- `1` = Nie dotyczy (не стосується)
- `2` = Nie (ні)

### 4.4 RodzajFaktury:

```xml
    <RodzajFaktury>VAT</RodzajFaktury>
```

Можливі значення:
- `VAT` - звичайний інвойс
- `KOR` - корегуюча
- `ZAL` - аванс

---

## 5. FaWiersz (Рядок товару/послуги) ⭐

Це найважливіша частина - тут описуються товари/послуги:

```xml
<FaWiersz>
    <NrWierszaFa>1</NrWierszaFa>
    <P_7>Nazwa produktu lub usługi</P_7>
    <P_8A>10.00</P_8A>
    <P_8AJ>szt</P_8AJ>
    <P_8B>1000.00</P_8B>
    <P_9A>1230.00</P_9A>
    <P_11>23</P_11>
    <P_12>230.00</P_12>
</FaWiersz>
```

### Поля FaWiersz детально:

| Поле | Опис | Обов'язкове | Приклад |
|------|------|-------------|---------|
| **NrWierszaFa** | Номер рядка | ✅ Так | `1` |
| **P_6A** | Kod CN (klasyfikacja towarowa) | ❌ Ні | `85234923` |
| **P_7** | ⭐ **Назва товару/послуги** | ✅ Так | `Laptop Dell Latitude` |
| **P_8A** | **Кількість** | ❌ Ні | `10.00` |
| **P_8AJ** | Одиниця виміру | ❌ Ні | `szt`, `kg`, `usł` |
| **P_8B** | ⭐ **Wartość netto** (сума без ПДВ) | ✅ Так | `1000.00` |
| **P_9A** | ⭐ **Wartość brutto** (сума з ПДВ) | ✅ Так | `1230.00` |
| **P_11** | Stawka VAT (%) | ❌ Ні* | `23` |
| **P_12** | Kwota VAT | ❌ Ні | `230.00` |
| **GTU** | Kod GTU (typ towaru) | ❌ Ні | `GTU_01` |

\* P_11 рекомендується, але не строго обов'язкове

### Одиниці виміру (P_8AJ):

Найпоширеніші:
- `szt` - sztuka (штука)
- `kg` - kilogram
- `g` - gram
- `m` - metr
- `m2` - metr kwadratowy
- `m3` - metr sześcienny
- `l` - litr
- `usł` - usługa (послуга)
- `godz` - godzina
- `kpl` - komplet

### Kody GTU (P_11_GTU):

GTU визначає тип товару для особливих процедур:
- `GTU_01` - Alkohol
- `GTU_02` - Towary energetyczne
- `GTU_03` - Samochody osobowe
- `GTU_04` - Wyroby tytoniowe
- `GTU_05` - Odpady
- `GTU_06` - Urządzenia elektroniczne
- `GTU_07` - Pojazdy lądowe
- `GTU_08` - Metale szlachetne
- `GTU_09` - Leki medyczne
- `GTU_10` - Budynki
- `GTU_11` - Świadczenie usług transportu pasażerskiego
- `GTU_12` - Usługi niematerialne
- `GTU_13` - Usługi inne

---

## 6. Приклад повного інвойсу з 2 товарами:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2023/06/29/12648/">
    <Naglowek>
        <KodFormularza kodSystemowy="FA (2)" wersjaSchemy="1-0E">FA</KodFormularza>
        <WariantFormularza>2</WariantFormularza>
        <DataWytworzeniaFa>2025-12-16T10:30:00</DataWytworzeniaFa>
        <SystemInfo>Odoo 16</SystemInfo>
    </Naglowek>
    <Podmiot1>
        <DaneIdentyfikacyjne>
            <NIP>9462527947</NIP>
            <Nazwa>Moja Firma Sp. z o.o.</Nazwa>
        </DaneIdentyfikacyjne>
        <Adres>
            <KodKraju>PL</KodKraju>
            <AdresL1>ul. Testowa 1</AdresL1>
            <AdresL2>00-000 Warszawa</AdresL2>
        </Adres>
    </Podmiot1>
    <Podmiot2>
        <DaneIdentyfikacyjne>
            <NIP>1234567890</NIP>
            <Nazwa>Klient ABC Sp. z o.o.</Nazwa>
        </DaneIdentyfikacyjne>
        <Adres>
            <KodKraju>PL</KodKraju>
            <AdresL1>ul. Kliencka 5</AdresL1>
            <AdresL2>01-000 Warszawa</AdresL2>
        </Adres>
    </Podmiot2>
    <Fa>
        <KodWaluty>PLN</KodWaluty>
        <P_1>2025-12-16</P_1>
        <P_2>FV/2025/001</P_2>
        <P_13_1>1500.00</P_13_1>
        <P_14_1>345.00</P_14_1>
        <P_15>1845.00</P_15>
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

        <!-- Товар 1 -->
        <FaWiersz>
            <NrWierszaFa>1</NrWierszaFa>
            <P_7>Laptop Dell Latitude 5420</P_7>
            <P_8A>2.00</P_8A>
            <P_8AJ>szt</P_8AJ>
            <P_8B>1000.00</P_8B>
            <P_9A>1230.00</P_9A>
            <P_11>23</P_11>
            <P_12>230.00</P_12>
        </FaWiersz>

        <!-- Товар 2 -->
        <FaWiersz>
            <NrWierszaFa>2</NrWierszaFa>
            <P_7>Myszka bezprzewodowa Logitech</P_7>
            <P_8A>5.00</P_8A>
            <P_8AJ>szt</P_8AJ>
            <P_8B>500.00</P_8B>
            <P_9A>615.00</P_9A>
            <P_11>23</P_11>
            <P_12>115.00</P_12>
        </FaWiersz>
    </Fa>
</Faktura>
```

---

## 7. Найчастіші помилки:

### ❌ Помилка 1: DataWytworzeniaFa без часу
```xml
<DataWytworzeniaFa>2025-12-16</DataWytworzeniaFa>  <!-- НЕ ПРАВИЛЬНО -->
```
✅ **Правильно:**
```xml
<DataWytworzeniaFa>2025-12-16T10:30:00</DataWytworzeniaFa>
```

### ❌ Помилка 2: NIP з префіксом PL
```xml
<NIP>PL9462527947</NIP>  <!-- НЕ ПРАВИЛЬНО -->
```
✅ **Правильно:**
```xml
<NIP>9462527947</NIP>
```

### ❌ Помилка 3: Відсутні обов'язкові Adnotacje
KSeF вимагає секцію `<Adnotacje>` з усіма обов'язковими полями.

### ❌ Помилка 4: Невірний порядок елементів
XML схема дуже строга щодо порядку елементів. Дотримуйтесь структури!

---

## 8. Корисні посилання:

- **GitHub KSeF Docs**: https://github.com/CIRFMF/ksef-docs
- **XSD Schema FA(2)**: Завантажити з https://ksef.podatki.gov.pl/baza-wiedzy-ksef/pliki-do-pobrania-ksef/
- **Portal KSeF**: https://ksef.mf.gov.pl
- **Test KSeF**: https://ksef-test.mf.gov.pl

---

## Автор

Документацію створено для проекту **bio_ksef2** - Odoo 16 інтеграція з KSeF.
