# Процес автентифікації KSeF API

## Загальна схема

```
1. Challenge         2. Encrypt Token    3. Init Auth       4. Wait (polling)   5. Redeem
   |                      |                   |                   |                   |
   v                      v                   v                   v                   v
[Server]  ------>  [Client шифрує]  ---> [Server дає]  ---> [Перевірка]  --->  [Фінальний токен]
  ^                                        temp token          статусу              для API
  |                                                               |
  └─────────────────────────────────────────────────────────────┘
                        (цикл 2 сек)
```

---

## Детальний опис кроків

### **Крок 1-3: Отримано `auth_data`**

```python
auth_data = resp.json()
# Відповідь від POST /api/v2/auth/ksef-token
```

**Приклад відповіді `auth_data`:**
```json
{
  "authenticationToken": {
    "token": "TEMP-TOKEN-12345-ABCDE-...",  ← Тимчасовий токен
    "type": "internal"
  },
  "referenceNumber": "20251212-CR-ABC123DEF456-789",  ← Номер для перевірки статусу
  "timestamp": "2025-12-12T10:30:00.000Z"
}
```

**Що ми робимо:**
```python
self.auth_token = auth_data['authenticationToken']['token']  # TEMP-TOKEN-12345...
self.reference_number = auth_data['referenceNumber']          # 20251212-CR-...
```

---

### **Крок 5: Чекаємо підтвердження (`_wait_for_authentication`)**

**Що робить цей метод:**
- Використовує **ТИМЧАСОВИЙ** токен `self.auth_token` для авторизації запитів
- Циклічно запитує сервер: "Чи підтверджена автентифікація?"
- Endpoint: `GET /api/v2/auth/{reference_number}`

**Заголовки запиту:**
```python
headers = {'SessionToken': self.auth_token}  # ← Використовуємо ТИМЧАСОВИЙ токен!
```

**Приклад запиту:**
```
GET https://ksef-test.mf.gov.pl/api/v2/auth/20251212-CR-ABC123DEF456-789
Headers:
  SessionToken: TEMP-TOKEN-12345-ABCDE-...
```

**Відповідь сервера (перевірка статусу):**
```json
{
  "status": {
    "code": 100,              ← Статус: 100-199 = в процесі
    "description": "Processing"
  },
  "timestamp": "2025-12-12T10:30:02.123Z"
}
```

**Через 2 секунди знову запитуємо...**
```json
{
  "status": {
    "code": 200,              ← Статус: 200 = УСПІХ! ✓
    "description": "Authorized"
  },
  "upo": "...",               ← Може містити додаткові дані
  "timestamp": "2025-12-12T10:30:04.456Z"
}
```

**Що означають статуси:**
- `100-199` → Автентифікація **в процесі** → продовжуємо чекати
- `200` → Автентифікація **підтверджена** → переходимо до кроку 6
- `300+` → **Помилка** → припиняємо роботу

---

### **Крок 6: Отримуємо фінальний токен (`_redeem_token`)**

**Що робить цей метод:**
- "Викупляє" (redeem) тимчасовий токен на **ФІНАЛЬНИЙ токен сесії**
- Цей фінальний токен використовується для всіх подальших API запитів
- Endpoint: `POST /api/v2/auth/token/redeem`

**Заголовки запиту:**
```python
headers = {'SessionToken': self.auth_token}  # ← Все ще тимчасовий токен
```

**Приклад запиту:**
```
POST https://ksef-test.mf.gov.pl/api/v2/auth/token/redeem
Headers:
  SessionToken: TEMP-TOKEN-12345-ABCDE-...
```

**Відповідь сервера (ФІНАЛЬНИЙ токен):**
```json
{
  "sessionToken": {
    "token": "SESSION-TOKEN-FINAL-67890-ZYXWV-...",  ← ЦЕ ФІНАЛЬНИЙ ТОКЕН!
    "context": {
      "contextIdentifier": {
        "type": "NIP",
        "identifier": "9462527947"
      },
      "contextName": {
        "type": "SUBJECT_NAME",
        "tradeName": "Назва компанії",
        "fullName": "Повна назва"
      },
      "credentialsRoleList": ["credentials_read", "invoice_read", "invoice_write"]
    },
    "credentials": {
      "type": "TOKEN",
      "roleDescription": "Токен KSeF"
    }
  },
  "referenceNumber": "20251212-CR-ABC123DEF456-789"
}
```

**Що ми робимо:**
```python
self.token = token_data['sessionToken']['token']  # SESSION-TOKEN-FINAL-67890...
self.session_context = token_data['sessionToken']['context']
```

---

## Підсумок: Різниця між токенами

| Токен | Призначення | Де використовується | Термін дії |
|-------|-------------|---------------------|------------|
| **`self.auth_token`** | Тимчасовий токен для перевірки статусу | Кроки 5-6 (перевірка + redeem) | Короткий (~5-10 хв) |
| **`self.token`** | Фінальний токен для роботи з API | Всі подальші запити (накладні, статус, тощо) | Довгий (~години/дні) |

---

## Код з поясненнями

```python
# Крок 4: Отримали відповідь від /auth/ksef-token
auth_data = resp.json()
# {
#   "authenticationToken": {"token": "TEMP-TOKEN-..."},
#   "referenceNumber": "20251212-CR-..."
# }

self.auth_token = auth_data['authenticationToken']['token']  # ТИМЧАСОВИЙ
self.reference_number = auth_data['referenceNumber']

# Крок 5: Чекаємо підтвердження
# GET /api/v2/auth/{reference_number}
# Headers: SessionToken = TEMP-TOKEN-...
# Відповідь: {"status": {"code": 200, "description": "Authorized"}}
if not self._wait_for_authentication():
    return  # Якщо статус != 200, виходимо

# Крок 6: Отримуємо ФІНАЛЬНИЙ токен
# POST /api/v2/auth/token/redeem
# Headers: SessionToken = TEMP-TOKEN-...
# Відповідь: {"sessionToken": {"token": "SESSION-TOKEN-FINAL-..."}}
if not self._redeem_token():
    return  # Якщо помилка, виходимо

# Тепер self.token містить ФІНАЛЬНИЙ токен для роботи з API!
print(f'Можна працювати з API, токен: {self.token}')
```

---

## Використання після автентифікації

```python
# Створюємо сесію
session = auth.Auth()

if session.token:
    # Використовуємо фінальний токен для запитів до API
    headers = {'SessionToken': session.token}

    # Приклад: Отримання статусу сесії
    resp = requests.get(
        f'{config.api_url}/api/v2/session/status',
        headers=headers
    )
    print(resp.json())
```
