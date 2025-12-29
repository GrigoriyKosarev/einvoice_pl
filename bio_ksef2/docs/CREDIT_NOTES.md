# Credit Notes (Faktury Korygujące) - KSeF Implementation

Документація по реалізації кредит нот для KSeF згідно з офіційною XSD схемою.

---

## 1. RodzajFaktury - Типи фактур

| Значення | Опис | Odoo тип | Примітка |
|----------|------|----------|----------|
| `VAT` | Faktura podstawowa | `out_invoice` | Звичайна фактура |
| `KOR` | Faktura korygująca | `out_refund` | **Звичайна кредит нота** ✅ |
| `KOR_ZAL` | Faktura korygująca fakturę zaliczkową | - | Кредит нота авансового інвойса (поки пропускаємо) |
| `KOR_ROZ` | Faktura korygująca fakturę rozliczeniową | `out_refund` (price_change=True) | Кредит нота зі зміною ціни ✅ |
| `ZAL` | Faktura zaliczkowa | - | Авансовий інвойс (prepayment) |
| `ROZ` | Faktura rozliczeniowa | - | Розрахунковий інвойс (final invoice) |
| `UPR` | Faktura uproszczona | - | Спрощена фактура (simplified) |

---

## 2. КРИТИЧНІ ВИМОГИ ⚠️

### ✅ DaneFaKorygowanej є ОБОВ'ЯЗКОВИМ для KOR!

**Елемент `<DaneFaKorygowanej>` є обов'язковим** для всіх типів кредит нот (`KOR`, `KOR_ZAL`, `KOR_ROZ`).

Без цього елемента KSeF відхилить фактуру з помилкою:
```
Błąd weryfikacji semantyki dokumentu faktury •
The element 'Fa' has invalid child element 'FaWiersz'.
List of possible elements expected: 'DaneFaKorygowanej'
```

### ✅ Як правильно створити кредит ноту в Odoo:

**ПРАВИЛЬНО** ✅:
1. Відкрити оригінальний інвойс
2. Натиснути кнопку **"Credit Note"** / **"Add Credit Note"**
3. Заповнити причину в поле **"Reason"** / **"Ref"**
4. Одно із полів `reversed_entry_id` автоматично заповниться

**НЕПРАВИЛЬНО** ❌:
- Створювати кредит ноту вручну (New → Customer Credit Note)
- При ручному створенні поле `reversed_entry_id` залишається порожнім
- KSeF відхилить таку кредит ноту!

### ✅ Валідація при відправці:

Якщо `reversed_entry_id` не заповнено, модуль покаже помилку:
```
Кредитна нота [номер] не має посилання на оригінальний інвойс!
Поле "reversed_entry_id" є обов'язковим для відправки кредитних нот в KSeF.
Створіть кредитну ноту через кнопку "Credit Note" на оригінальному інвойсі.
```

---

## 3. Структура DaneFaKorygowanej

### Обов'язкові поля (для RodzajFaktury = KOR, KOR_ZAL, KOR_ROZ):

```xml
<DaneFaKorygowanej>
    <DataWystFaKorygowanej>2025-12-15</DataWystFaKorygowanej>
    <NrFaKorygowanej>SI/2025/001</NrFaKorygowanej>
    <choice>
        <!-- Якщо оригінальна фактура в KSeF: -->
        <NrKSeF>1</NrKSeF>
        <NrKSeFFaKorygowanej>1234567890123456789012345678901234567890</NrKSeFFaKorygowanej>

        <!-- АБО якщо оригінальна фактура поза KSeF: -->
        <NrKSeFN>1</NrKSeFN>
    </choice>
</DaneFaKorygowanej>
```

### Мапування полів з Odoo:

| XSD поле | Odoo поле | Примітка |
|----------|-----------|----------|
| `DataWystFaKorygowanej` | `reversed_entry_id.invoice_date` | Дата оригінального інвойса |
| `NrFaKorygowanej` | `reversed_entry_id.name` | Номер оригінального інвойса |
| `NrKSeFFaKorygowanej` | `reversed_entry_id.ksef_number` | KSeF номер оригінального інвойса |

### Типи choice:

1. **Фактура в KSeF**:
   - `<NrKSeF>1</NrKSeF>` - маркер що фактура в KSeF
   - `<NrKSeFFaKorygowanej>` - KSeF номер (формат: 40 символів)

2. **Фактура поза KSeF**:
   - `<NrKSeFN>1</NrKSeFN>` - маркер що фактура поза KSeF

---

## 4. TypKorekty - Тип коrekції

Впливає на **період відображення в обліку ПДВ**:

| Значення | Опис | Коли використовувати |
|----------|------|---------------------|
| `1` | Korekta skutkująca w dacie ujęcia faktury pierwotnej | Корекція діє від дати **оригінальної** фактури |
| `2` | Korekta skutkująca w dacie wystawienia faktury korygującej | Корекція діє від дати **кредит ноти** (найчастіше) ✅ |
| `3` | Korekta skutkująca w dacie innej | Корекція діє від **іншої дати** |

**Рекомендація**: Використовувати `2` за замовчуванням (корекція в даті виписування кредит ноти).

---

## 5. PrzyczynaKorekty - Причина корекції

```xml
<PrzyczynaKorekty>Zwrot towaru</PrzyczynaKorekty>
```

**Мапування з Odoo**: стандартне поле `ref` кредит ноти (Reason/Reference)

**Приклади причин**:
- "Zwrot towaru" (повернення товару)
- "Błąd w cenie" (помилка в ціні)
- "Reklamacja" (рекламація)
- "Rabat" (знижка)

---

## 6. Суми в кредит нотах - КРИТИЧНО! ⚠️

**Згідно з XSD документацією (рядок 2355)**:
> "W przypadku wystawienia faktury korygującej, wypełnia się wszystkie pola wg stanu po korekcie,
> a pola dotyczące podstaw opodatkowania, podatku oraz należności ogółem wypełnia się **poprzez różnicę**"

### Правило:
- Всі описові поля (P_7, P_8A, тощо) - згідно зі станом **ПІСЛЯ** корекції
- Суми (P_13_*, P_14_*, P_15) - як **РІЗНИЦЯ** (нова сума - стара сума)

### Формат сум:

**Повернення товару (100% кредит нота)**:
```
Оригінальна фактура: 1000.00 EUR
Кредит нота: -1000.00 EUR
```

**Часткове повернення (50% кредит нота)**:
```
Оригінальна фактура: 1000.00 EUR
Кредит нота: -500.00 EUR
```

**Важливо**: Суми в кредит нотах зазвичай **від'ємні** (різниця = нове - старе = 0 - 1000 = -1000)

---

## 7. Приклад XML для кредит ноти (KOR)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Faktura xmlns="http://crd.gov.pl/wzor/2023/06/29/12648/">
    <Naglowek>
        <KodFormularza kodSystemowy="FA (2)" wersjaSchemy="1-0E">FA</KodFormularza>
        <WariantFormularza>2</WariantFormularza>
        <DataWytworzeniaFa>2025-12-23T15:30:00</DataWytworzeniaFa>
        <SystemInfo>Odoo KSeF Integration</SystemInfo>
    </Naglowek>

    <Podmiot1><!-- Продавець --></Podmiot1>
    <Podmiot2><!-- Покупець --></Podmiot2>

    <Fa>
        <KodWaluty>PLN</KodWaluty>
        <P_1>2025-12-23</P_1>                    <!-- Дата кредит ноти -->
        <P_2>CN/2025/001</P_2>                   <!-- Номер кредит ноти -->

        <!-- Суми як РІЗНИЦЯ (від'ємні для повернення) -->
        <P_13_1>-1000.00</P_13_1>                <!-- Різниця нетто 23% -->
        <P_14_1>-230.00</P_14_1>                 <!-- Різниця ПДВ 23% -->
        <P_15>-1230.00</P_15>                    <!-- Різниця total -->

        <Adnotacje><!-- ... --></Adnotacje>

        <!-- ГОЛОВНЕ: Тип фактури = KOR -->
        <RodzajFaktury>KOR</RodzajFaktury>

        <!-- Причина корекції -->
        <PrzyczynaKorekty>Zwrot towaru</PrzyczynaKorekty>

        <!-- Тип корекції -->
        <TypKorekty>2</TypKorekty>

        <!-- Дані оригінальної фактури -->
        <DaneFaKorygowanej>
            <DataWystFaKorygowanej>2025-12-15</DataWystFaKorygowanej>
            <NrFaKorygowanej>SI/2025/001</NrFaKorygowanej>
            <NrKSeF>1</NrKSeF>
            <NrKSeFFaKorygowanej>1234567890123456789012345678901234567890</NrKSeFFaKorygowanej>
        </DaneFaKorygowanej>

        <!-- Рядки фактури -->
        <FaWiersz>
            <NrWierszaFa>1</NrWierszaFa>
            <P_7>Product A (zwrot)</P_7>
            <P_8A>szt</P_8A>
            <P_8B>-10.00</P_8B>                  <!-- Кількість від'ємна -->
            <P_9A>100.00</P_9A>                  <!-- Ціна за одиницю (додатня) -->
            <P_11>-1000.00</P_11>                <!-- Сума нетто (від'ємна) -->
            <P_12>23</P_12>                      <!-- Ставка ПДВ -->
        </FaWiersz>
    </Fa>
</Faktura>
```

---

## 8. Відмінності KOR vs KOR_ROZ

### KOR (звичайна кредит нота):
- Будь-які зміни в інвойсі
- Повернення товару
- Виправлення помилок
- **НЕ потребує** додаткових полів

### KOR_ROZ (art. 106f ust. 3):
- **Тільки** для опустів/знижок за період
- Один покупець, багато поставок за період
- Потребує додаткове поле `<OkresFaKorygowanej>` - період дії знижки

**Приклад OkresFaKorygowanej**:
```xml
<OkresFaKorygowanej>2025-01-01 - 2025-01-31</OkresFaKorygowanej>
```

---

## 9. Логіка визначення типу в Odoo

```python
def get_rodzaj_faktury(invoice):
    """Визначає тип фактури для KSeF"""

    # Кредит нота
    if invoice.move_type == 'out_refund':
        # Перевіряємо чи це знижка за період (price change)
        # В Odoo це можна визначити через custom поле або logic
        if hasattr(invoice, 'is_period_discount') and invoice.is_period_discount:
            return 'KOR_ROZ'
        else:
            return 'KOR'

    # Звичайна фактура
    elif invoice.move_type == 'out_invoice':
        return 'VAT'

    else:
        raise ValueError(f"Unsupported invoice type: {invoice.move_type}")
```

---

## 10. Реалізовані зміни в Odoo моделі

### account.move (додані поля):

```python
class AccountMove(models.Model):
    _inherit = 'account.move'

    # Стандартні Odoo поля використовувані для кредит нот:
    # - reversed_entry_id: зв'язок з оригінальним інвойсом
    # - ref: причина корекції (PrzyczynaKorekty)

    # Додане поле для KSeF:
    ksef_correction_type = fields.Selection([
        ('1', 'W dacie faktury pierwotnej'),
        ('2', 'W dacie faktury korygującej'),
        ('3', 'W innej dacie'),
    ], string='KSeF Correction Type', default='2',
       help='Typ skutku korekty (TypKorekty)')
```

**Примітка**: Використовується стандартне поле `ref` (Reason/Reference) для зберігання причини корекції замість створення окремого поля.

---

## 11. Статус імплементації

1. ✅ Проаналізувати XSD схему
2. ✅ Додати підтримку RodzajFaktury = KOR
3. ✅ Реалізувати DaneFaKorygowanej блок
4. ✅ Додати PrzyczynaKorekty та TypKorekty
5. ✅ Обробка від'ємних сум (автоматично в Odoo)
6. ✅ Валідація обов'язкового reversed_entry_id для кредит нот
7. ✅ Валідація обов'язкового DaneFaKorygowanej в XML генераторі
8. ✅ Оновлена документація з критичними вимогами
9. ⏳ (Опціонально) Підтримка KOR_ROZ для знижок за період

---

**Джерело**: `/home/user/einvoice_pl/bio_ksef2/docs/FA3/schemat.xsd`
**Дата**: 24 грудня 2025
