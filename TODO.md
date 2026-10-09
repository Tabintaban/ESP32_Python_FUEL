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
- [x] Архитектурный план `ESP32_MicroPython_Architecture_Plan.md`
- [x] Лицензия MIT

### Криптография (v1.0)
- [x] `crypto_manager.py` — «fake AES-GCM» (заменено)
- [x] `lightweight_security.py` — «broken Ed25519» (заменено)
- [x] `_derive_private_from_public()` — небезопасный метод (удалён)

### Криптография (v2.0)
- [x] `crypto_manager.py` — AES-CTR + HMAC-SHA256 (Encrypt-then-MAC)
- [x] `crypto_manager.py` — constant-time comparison
- [x] `crypto_manager.py` — fail-secure при отсутствии `ucryptolib`
- [x] `lightweight_security.py` — HMAC-SHA256 вместо Ed25519
- [x] `lightweight_security.py` — nonce/timestamp против replay
- [x] `lightweight_security.py` — constant-time comparison

### Песочница (v2/v3)
- [x] `execution_sandbox.py` — SafeImporter с whitelist
- [x] `execution_sandbox.py` — таймаут через WDT + кормящий таймер
- [x] `execution_sandbox.py` — блокировка `__import__`, `eval`, `exec`
- [x] `execution_sandbox.py` — интеграция `RealTimeMemoryMonitor`
- [x] `memory_optimizer.py` — pre/during/after execution checks

### Компиляция и загрузка
- [x] `line_compiler.py` — нормализация отступов (GCD)
- [x] `line_compiler.py` — запрет смешивания табов и пробелов
- [x] `fast_json_loader.py` — сохранение переносов строк
- [x] `fast_json_loader.py` — валидация синтаксиса
- [x] `program_loader.py` — загрузка и валидация JSON

### Прочее
- [x] `main.py` — Logger с уровнями
- [x] `main.py` — конкретные типы исключений
- [x] `test_results.txt` — тесты (но криптография пропущена)
- [x] `performance_tests.py` — бенчмарки

---

## Часть 2. Что сделано в нашей работе

### Шаг 2.5 — whitelist модулей в песочнице
- [x] Убраны из whitelist: `sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`
- [x] Оставлены: `machine`, `time`, `math`, `struct`, `json`, `gc`
- [x] Синтаксис проверен (`ast.parse`) — OK
- [x] Соответствие TUR55 раздел 6 — достигнуто

### Шаг 3.1 — AES-256-GCM на чистом Python
- [x] 3.1.1 — создан `gcm.py` со скелетом
- [x] 3.1.1 — создан `test_gcm.py` с NIST-векторами (TC13, TC14, TC15)
- [x] 3.1.2.1 — реализованы `_gctr`, `_inc32`, IV, тег
- [x] 3.1.2.2 — реализован `_ghash` (побитовый)
- [x] 3.1.2.2 — реализован `_gf_mul` (GF(2^128))
- [x] NIST-тесты на CPython: **3/3 прошло**
- [x] Проверка `_gf_mul` (NIST TC2): OK
- [x] Бенчмарк на CPython: 10 KB = 57 мс encrypt + 57 мс decrypt

### Попытка табличного GHASH (откат)
- [x] Реализован `_precompute_table` + `_ghash` табличный (4-бит)
- [x] **Откат** — табличный GHASH дал неверные результаты
- [x] Возврат к побитовому `_ghash`

### Шаг 3.1.5 — перенос на ESP32
- [x] Установлен `esptool` 5.5.0
- [x] Скачана прошивка `ESP32_GENERIC-20260824-v1.29.0.bin`
- [x] Стереть flash ESP32
- [x] Залита MicroPython 1.29.0
- [x] Установлен MicroPico (VSCode)
- [x] Подключение к ESP32 (COM3) работает
- [x] Проверено: `ucryptolib` доступен
- [x] Создан `gcm_esp32.py` (только `ucryptolib`, без `cryptography`)
- [x] Залит `gcm_esp32.py` на ESP32
- [x] Создан `test_gcm_esp32.py`
- [x] Залит `test_gcm_esp32.py` на ESP32

### Шаг 3.1.5 — отладка на ESP32
- [x] NIST-тесты на ESP32: **1/3** (TC13 OK, TC14/TC15 FAIL)
- [x] Исправлен `_gctr` (паддинг до 16 байт) — `ValueError: blksize % 16` устранён
- [x] Проверен `_gf_mul` на ESP32 — **работает** (5e2ec746...)
- [x] Проверен `_ghash` на ESP32 — **работает** (нули для пустого блока)
- [x] Выяснено: `ucryptolib` на ESP32 **не поддерживает**:
  - CTR (mode=6) → `ValueError: mode`
  - GCM (mode=0) → `ValueError: mode`
- [x] Подтверждено: **GCM недоступен** на стандартной прошивке

---

## Часть 3. Что нужно сделать

### Криптография — заблокировано
- [ ] ❌ Получить GCM на ESP32 (заблокировано отсутствием режима)
- [ ] ⏳ Поиск/сборка прошивки MicroPython с GCM
  - [ ] Установить ESP-IDF
  - [ ] Клонировать MicroPython
  - [ ] Включить `MICROPY_PY_CRYPTOOLIB_GCM`
  - [ ] Собрать прошивку
  - [ ] Залить и проверить
- [ ] Если GCM недоступен — **вернуться к CTR+HMAC** и честно заявить отклонение от TUR55

### Формат пакета TUR55 (раздел 3.4)
- [ ] Реализовать структуру пакета:
  - [ ] `[HEADER: TUR55v1]`
  - [ ] `[ENCRYPTED_SESSION_KEY]` (ECIES / RSA-OAEP)
  - [ ] `[ENCRYPTED_SCRIPT]` (AES-256-GCM)
  - [ ] `[SIGNATURE]` (Ed25519 / ECDSA secp256k1)
- [ ] JSON-конверт по разделу 3.2:
  - [ ] `tur55_version`
  - [ ] `command_id`
  - [ ] `device_id`
  - [ ] `source`
  - [ ] `execution`
  - [ ] `custom_data`

### Сессионный ключ (ECIES / RSA-OAEP)
- [ ] Выбрать: ECIES или RSA-OAEP
- [ ] Реализовать на ESP32
- [ ] Асимметричное шифрование сессионного ключа

### Подпись (Ed25519 / ECDSA secp256k1)
- [ ] Выбрать: Ed25519 или ECDSA
- [ ] Реализовать на ESP32
- [ ] `lightweight_security.py` — заменить HMAC на асимметричную подпись

### Хеширование (SHA3-256 / Blake2s)
- [ ] Заменить SHA-256 на SHA3-256 или Blake2s

### Ключи (раздел 4)
- [ ] Реализовать хранение ключей в eFuse / Secure Element
- [ ] Убрать ключи из кода

### `program_loader.py`
- [ ] Исправить вызов `verify_ed25519_signature` (метод не существует)
- [ ] Добавить проверку `expires` (раздел 5 TUR55)
- [ ] Добавить проверку `command_id` (replay)

### `execution_engine.py`
- [ ] Добавить проверку `expires` в цикл

### Песочница
- [ ] Убрать `object_factory.py` или обезопасить (там `exec()` без песочницы)

### Тесты
- [ ] Запустить **все** тесты на реальном ESP32
- [ ] Добавить тесты для `program_loader`
- [ ] Добавить тесты для формата пакета TUR55

### Документация
- [ ] README — обновить статус TUR55
- [ ] CHANGELOG — записать всё сделанное
- [ ] Отдельный документ `TUR55_COMPLIANCE.md` — таблица соответствия

### Продакшн
- [ ] Аудит безопасности
- [ ] Стресс-тесты на ESP32
- [ ] Документация для пользователей
- [ ] Обработка ошибок (потеря питания, обрыв связи)

---

## Текущий статус

**Готово:** ~60% работы  
**Заблокировано:** GCM на ESP32 (нужна кастомная прошивка)  
**Осталось:** формат пакета, подпись, ECIES, eFuse, тесты, документация

**Ключевая проблема:** стандартная прошивка MicroPython для ESP32 **не поддерживает GCM**. TUR55 требует GCM. Без кастомной прошивки — **TUR55/Bronze недостижим**.