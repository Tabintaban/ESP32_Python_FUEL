# TODO — ESP32_Python_FUEL / TUR55

Цель: привести проект к стандарту TUR55/Bronze **без отклонений**.

Легенда:
- [x] — сделано
- [ ] — TODO
- ⏳ — в работе
- ❌ — заблокировано

---

## Часть 1. Что было сделано ДО начала работы

### Инфраструктура
- [x] Создан проект `ESP32_Python_FUEL`
- [x] Разработаны 14 Python-модулей
- [x] Написаны 5 тестовых файлов
- [x] Документация (README EN/RU, PROJECT_SUMMARY EN/RU, CHANGELOG)
- [x] Архитектурный план
- [x] Лицензия MIT

### Криптография (v2.0)
- [x] `crypto_manager.py` — AES-CTR + HMAC-SHA256
- [x] `lightweight_security.py` — HMAC-SHA256
- [x] Constant-time comparison

### Песочница (v2/v3)
- [x] `execution_sandbox.py` — SafeImporter с whitelist
- [x] `execution_sandbox.py` — таймаут через WDT
- [x] `memory_optimizer.py` — pre/during/after checks

---

## Часть 2. Что сделано в нашей работе

### Шаг 2.5 — whitelist модулей
- [x] Убраны: `sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`
- [x] Оставлены: `machine`, `time`, `math`, `struct`, `json`, `gc`
- [x] Соответствие TUR55 раздел 6 — **достигнуто**

### Шаг 3.1 — Кастомная прошивка MicroPython
- [x] Установлен WSL Ubuntu 22.04
- [x] Установлен ESP-IDF **v5.2.2** (v5.1.2 и v5.3.2 не подошли)
- [x] Клонирован MicroPython **v1.24.1**
- [x] Собран `mpy-cross`
- [x] **Решение boot loop:** заливать **три файла** по трём адресам:
  - `bootloader.bin` → `0x1000`
  - `partition-table.bin` → `0x8000`
  - `micropython.bin` → `0x10000`

### Шаг 3.2 — GCM C-модуль
- [x] Создан `~/cmodules/gcm/modgcm.c` (mbedTLS)
- [x] Создан `~/cmodules/gcm/micropython.cmake`
- [x] **NIST SP 800-38D на ESP32: 3/3 прошло**
- [x] `gcm.encrypt(key, iv, pt, aad)` → `(ct, tag)`
- [x] `gcm.decrypt(key, iv, ct, tag, aad)` → `pt`

### Шаг 3.3 — ucryptography (Ed25519, BLAKE2s, RSA-OAEP, ECDSA)
- [x] Клонирован `ucryptography`
- [x] Обёртка `mp_obj_int_to_bytes` для MicroPython v1.24.1
- [x] Заглушки 3DES (`des3_stubs.c`)
- [x] **RSA-OAEP работает** (`b'secret'` round-trip)
- [x] **BLAKE2s работает** (`f308fc02...`)
- [x] **ECDSA SECP256R1 работает**
- [x] **Ed25519 работает, НО с багом** на сообщениях > 96 байт
  - Решение: **заменён на secp256k1**

### Шаг 3.4 — secp256k1 (Bitcoin Core)
- [x] Клонирован `secp256k1-embedded-ecdh`
- [x] Модуль `usecp256k1` загружается на ESP32
- [x] **ECDSA sign / verify работает**
- [x] **Точное соответствие TUR55 раздел 4**

### Шаг 3.5 — Формат пакета TUR55
- [x] Создан `tur55_packet.py` (JWE-inspired)
- [x] Структура: HEADER + PUBKEY + SESSION_KEY + SCRIPT + SIGNATURE
- [x] Подпись **ECDSA secp256k1** (вместо Ed25519)
- [x] `build_packet()` — для экзекутора
- [x] `parse_packet()` — для ESP32
- [x] Создан `gcm_adapter.py` — единый интерфейс GCM
- [x] Тест на CPython: **round-trip прошёл**
- [x] Tamper detection: **работает**
- [x] Залито на ESP32: `tur55_packet.py`, `gcm_adapter.py`
- [x] `import tur55_packet` на ESP32: **OK**

---

## Часть 3. Что нужно сделать

### Шаг 3.6 — Round-trip тест (CPython → ESP32)
- [x] Создан `build_packet_cpython.py` (CPython-версия build_packet)
- [x] Использован `embit` вместо `coincurve` (совместим с `usecp256k1`)
- [x] Пакет сгенерирован на CPython: 521 байт
- [x] Создан `esp32_private_key.json` (RSA компоненты: n, e, d, p, q, dmp1, dmq1, iqmp)
- [x] Создан `executor_pubkey.bin` (33 байта)
- [x] Создан `decrypt_packet_esp32.py` (расшифровка на ESP32)
- [x] **Проверка RSA-OAEP self-test:** работает
- [x] **Проверка ECDSA (embit vs usecp256k1):** работает
- [x] **ROUND-TRIP: УСПЕХ** ✅
  - CPython: JSON → ECDSA sign → RSA-OAEP → AES-GCM → пакет
  - ESP32: пакет → ECDSA verify → RSA-OAEP decrypt → AES-GCM decrypt → JSON
  - Результат: `{'tur55_version': '1.0', 'command_id': '0x7e5f8a3c', 'device_id': 'esp32_001', 'script': "print('hello from ESP32')"}`

### Формат пакета TUR55 — тестирование
- [x] Полный round-trip: сгенерировать пакет на CPython → залить на ESP32 → расшифровать
- [x] Проверить `parse_packet` на ESP32 с реальным пакетом
- [ ] JSON-конверт по разделу 3.2: `tur55_version`, `command_id`, `device_id`, `source`, `execution`, `custom_data`

### Интеграция
- [ ] `program_loader.py` — использовать `tur55_packet.parse_packet()`
- [ ] Исправить вызов `verify_ed25519_signature` (метод не существует)
- [ ] Добавить проверку `expires` (раздел 5 TUR55)
- [ ] Добавить проверку `command_id` (replay protection)
- [ ] `execution_engine.py` — проверка `expires` в цикле
- [ ] Заменить SHA-256 на **BLAKE2s** в `program_loader.py`

### Ключи (раздел 4)
- [ ] Хранение ключей в **eFuse** (ESP32)
- [ ] Убрать ключи из кода
- [ ] Загрузка ключей при старте

### Сетевой стек (по умолчанию)
- [ ] MQTT-клиент (`umqtt.simple`)
- [ ] HTTP-сервер (опционально)
- [ ] Приём пакетов по сети
- [ ] Единый интерфейс приёма (сеть + файл)

### Физическая доставка
- [ ] Чтение `programs/program.enc` из файловой системы
- [ ] Единый интерфейс с сетевым приёмом

### Песочница
- [ ] Убрать `object_factory.py` или обезопасить (`exec()` без песочницы)
- [ ] Доступ к GPIO только по разрешённым пинам

### Тесты
- [ ] Запустить **все** тесты на реальном ESP32
- [ ] Тесты для `program_loader`
- [ ] Тесты для формата пакета TUR55

### Документация
- [ ] README — обновить статус TUR55
- [ ] CHANGELOG — записать всё сделанное
- [ ] `TUR55_COMPLIANCE.md` — таблица соответствия
- [ ] `BUILD_GCM_FIRMWARE.md` — обновить (добавить ucryptography + secp256k1)
- [ ] `FIRMWARE_WITH_UCRYPTOGRAPHY.md` — обновить

### Продакшн
- [ ] Аудит безопасности
- [ ] Стресс-тесты на ESP32
- [ ] Обработка ошибок (потеря питания, обрыв связи)

---

## Текущий статус

**Готово:** **~55%** TUR55/Bronze

| Раздел | Статус |
|---|---|
| **Раздел 3.4** — формат пакета | ✅ **РАБОТАЕТ end-to-end** |
| **Раздел 4** — AES-256-GCM | ✅ NIST 3/3 |
| **Раздел 4** — ECDSA secp256k1 | ✅ Работает |
| **Раздел 4** — RSA-OAEP | ✅ Работает |
| **Раздел 4** — BLAKE2s | ✅ Работает |
| **Раздел 4** — eFuse | ❌ |
| **Раздел 5** — expires / command_id | ❌ |
| **Раздел 6** — whitelist / таймаут / память | ✅ |

**Что сделано:**
- ✅ Кастомная прошивка MicroPython v1.24.1 + ESP-IDF v5.2.2
- ✅ GCM C-модуль
- ✅ ucryptography (RSA-OAEP, BLAKE2s)
- ✅ secp256k1 (Bitcoin Core)
- ✅ Формат пакета TUR55


**Что осталось:**
- Интеграция в `program_loader.py`
- Проверка `expires` и `command_id`
- eFuse
- Сетевой стек (MQTT)
- Физическая доставка
- Документация