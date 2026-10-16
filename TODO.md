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
- [x] Документация (README EN/RU, CHANGELOG)
- [x] `PROJECT_SUMMARY.md` / `_RU.md` — удалены (устарели)
- [x] `ESP32_MicroPython_Architecture_Plan.md` — удалён (устарел)
- [x] Архитектурный план
- [x] Лицензия MIT

### Криптография (v2.0) — УСТАРЕЛО
- [x] `crypto_manager.py` — AES-CTR + HMAC-SHA256 _(заменён на GCM)_
- [x] `lightweight_security.py` — HMAC-SHA256 _(заменён на ECDSA)_
- [x] Constant-time comparison _(в GCM не нужно — тег проверяется атомарно)_

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

### Шаг 3.6 — Round-trip тест (CPython → ESP32)
- [x] Создан `build_packet_cpython.py` (CPython-версия build_packet)
- [x] Использован `embit` вместо `coincurve` (совместим с `usecp256k1`)
- [x] Создан `esp32_private_key.json` (RSA компоненты: n, e, d, p, q, dmp1, dmq1, iqmp)
- [x] Создан `executor_pubkey.bin` (33 байта)
- [x] Создан `decrypt_packet_esp32.py` (расшифровка на ESP32)
- [x] **ROUND-TRIP: УСПЕХ** ✅

### Шаг 3.7 — Интеграция `program_loader.py` (Заход 1)
- [x] `program_loader.py` переписан под `tur55_packet.parse_packet()`
- [x] Валидация конверта 3.2: `tur55_version`, `command_id`, `device_id`, `source`, `execution`, `custom_data`
- [x] `load_program(packet_bytes)` — основной вход (transport-independent)
- [x] `load_program_from_file(filepath)` — обёртка для файла
- [x] Загрузка ключей в `__init__()` (RSA + executor pubkey)
- [x] Удалён мёртвый код: `validate_signature`, `verify_integrity`, `CryptoManager`, `LightweightSecurity`
- [x] `validate_permissions` — из `execution.permissions`
- [x] `validate_runtime_constraints` — из `execution`
- [x] Кэш по `command_id`
- [x] `tur55_packet.py` — добавлен embit для CPython (`_ecdsa_sign`, `_ecdsa_verify`)
- [x] `build_packet_cpython.py` — обновлён под конверт 3.2
- [x] `test_program_loader.py` — тест на CPython: **пройден**

### Шаг 3.8 — Replay protection + expires (Заход 2)
- [x] `validate_expires` — опциональная проверка (только при `time_synced`)
- [x] `validate_command_id` — replay protection (FIFO, 100 записей)
- [x] `set_time(current_time)` — API для синхронизации времени
- [x] `used_command_ids` + `used_command_ids_set`
- [x] NVS — сохранение между перезагрузками (Шаг 3.12)
- [x] `test_loader_replay.py` — тест на CPython: **пройден**
- [x] `test_esp32.py` — тест на ESP32: **пройден**
  - Первый `load_program` → OK
  - Второй `load_program` → `Command replay detected` ✅

### Шаг 3.9 — Интеграция `execution_engine.py` (Вариант 1+2)
- [x] `execute_program(program_data)` принимает конверт 3.2
- [x] Раскладка `execution.functions` + `execution.setup` + `execution.loop_logic`
- [x] Setup-контекст передаётся в loop (`merged` globals + locals)
- [x] `hot_swap(new_program)` под конверт 3.2 (`command_id`)
- [x] Лимиты из пакета применяются к sandbox через `limit_resources()`
- [x] Восстановление лимитов в `finally`
- [x] `test_engine_cpython.py` — тест на CPython: **пройден**

### Шаг 3.10 — TUR55 на ESP32 (совместимость с MicroPython)
- [x] Убран WDT из `execution_sandbox.py` (в MicroPython `deinit` не работает)
- [x] Кооперативный таймаут через `machine.Timer(-1)` + флаги
- [x] Убрана подмена `sys.stdout`/`sys.stderr` (в MicroPython их нет)
- [x] Убран перехват `print` (в MicroPython невозможно через `__builtins__`)
- [x] `tur55_packet.py` — `except (ImportError, NameError)` для `vars`
- [x] `execution_sandbox.py` — `getattr(sys, 'stdout', None)` + проверки
- [x] `execution_engine.py` — `capture_output=False` для setup/loop
- [x] `test_engine_esp32.py` — тест на ESP32: **пройден**
  - setup: OK
  - loop: 5 итераций
  - без WDT-сбросов

### Шаг 3.11 — `main.py` — стандартный пайплайн
- [x] Переписан целиком (убрана старая схема: CryptoManager, ObjectFactory, FastJSONLoader, LineBasedCompiler, LightweightSecurity)
- [x] `Logger` — оставлен (5 уровней)
- [x] `run_program(path, max_iterations, log_level)` — пайплайн
- [x] `main()` — с try/except/finally
- [x] Логи: `command_id`, `device_id`, `permissions`, лимиты
- [x] Логи: setup success, loop iterations, time, stats
- [x] `gc.collect()` в finally
- [x] **Тест на CPython: пройден** (`loop time_ms: 156`)
- [x] **Тест на ESP32: пройден** (`loop time_ms: 227`)
- [x] Docstring перечисляет расширения (для Расширенной версии)

### Шаг 3.12 — NVS для `used_command_ids`
- [x] `_load_used_command_ids()` — загрузка из NVS при старте
- [x] `_save_used_command_ids()` — сохранение в NVS при новом `command_id`
- [x] Fallback на RAM (CPython — NVS недоступен)
- [x] Проверка на ESP32: replay переживает Ctrl+D
- [x] Тест на CPython: работает как раньше

### Шаг 3.13 — MQTT (Delivery Layer TUR55)
- [x] `umqtt.simple` установлен на ESP32 (`mip install`)
- [x] `paho-mqtt` установлен на CPython
- [x] `mqtt_client.py` — приём пакетов (`MQTTReceiver`)
- [x] `mqtt_publisher.py` — отправка пакетов (`paho-mqtt`)
- [x] Wi-Fi подключение (`network.WLAN`)
- [x] **Проверено end-to-end:** CPython → MQTT → ESP32 (862 байта)
- [x] **Полный пайплайн:** `mqtt_client` → `program_loader` → `execution_engine`
- [x] Соответствие TUR55 тезис 8 (Transport Freedom)

### Шаг 3.14 — NTP (источник времени для `expires`)
- [x] `time_sync.py` — NTP через Wi-Fi
- [x] `sync_time(ssid, password)` — синхронизация
- [x] `EPOCH_OFFSET = 946684800` (MicroPython → Unix)
- [x] Retry — 3 попытки, пауза 2 сек
- [x] `main.py` — опциональный NTP-вызов
- [x] `secrets.py` — Wi-Fi настройки (в `.gitignore`)
- [x] **Проверено:** `+3600` → принят, `-3600` → `Command expired`

### Шаг 3.15 — Физическая доставка (`programs/program.enc`)
- [x] Папка `programs/` на ESP32 — создана
- [x] `main._find_packet()` — ищет `programs/program.enc`, потом `test_packet_engine.bin`
- [x] `run_program(packet_path=None)` — автопоиск
- [x] `programs/*.enc` — в `.gitignore`
- [x] `programs/readme.md` — обновлён
- [x] **Проверено на ESP32:** `Auto-found packet: programs/program.enc`
- [x] Соответствие TUR55 тезис 8 (Transport Freedom — офлайн)

### Шаг 3.16 — Лог в UART (TUR55/Bronze, раздел 9)
- [x] `Logger` — 5 уровней (DEBUG–CRITICAL)
- [x] События запуска: `=== TUR55 Pipeline ===`
- [x] События пакета: `Auto-found packet`, `command_id`, `device_id`
- [x] События исполнения: `setup success`, `loop iterations`, `loop time_ms`
- [x] События завершения: `=== Done ===`
- [x] На ESP32: `print()` → UART0 → USB → COM → miniterm
- [x] На CPython: `print()` → консоль
- [x] **TUR55/Bronze — закрыт полностью**

### Шаг 3.17 — CPython-проверка
- [x] `test_program_loader.py` — пройден
- [x] `test_loader_replay.py` — пройден (4/4)
- [x] `test_engine_cpython.py` — пройден
- [x] `test_gcm.py` — NIST 3/3
- [x] `tests/` (pytest) — 5/5 пройдено
- [x] `py main.py` — полный пайплайн работает
- [x] Удалены устаревшие: `test_hash.py`, `test_tur55_packet.py`
- [x] `tests/test_execution_sandbox.py` — обновлён под новый API

### Документация проекта
- [x] `.gitignore` — обновлён (`__pycache__`, `*.pyc`, `esp32_private_key.*`, `test_packet*.bin`, `executor_pubkey.bin`)

---

## Часть 3. Что нужно сделать

### Ключи (раздел 4) — для Gold
- [ ] Хранение ключей в **eFuse** (ESP32) — **Gold уровень** (не Bronze)
- [ ] Убрать `esp32_private_key.json` и `executor_pubkey.bin` из файловой системы
- [ ] Загрузка ключей при старте
- [ ] **Secure boot** — **Gold уровень**

### Сетевой стек
- [x] MQTT-клиент (`umqtt.simple`) — `mqtt_client.py`
- [x] MQTT-издатель (`paho-mqtt`) — `mqtt_publisher.py`
- [x] Приём пакетов по сети — проверено на ESP32 (862 байта)
- [ ] HTTP-сервер (опционально)
- [ ] Единый интерфейс приёма (сеть + файл) — `run_from_bytes(packet)`

### Физическая доставка
- [x] Чтение `programs/program.enc` из файловой системы — `main._find_packet()`
- [x] Единый интерфейс с сетевым приёмом — `load_program(packet_bytes)`
- [x] Папка `programs/` на ESP32 — создана
- [x] `programs/*.enc` — в `.gitignore`
- [x] `programs/readme.md` — обновлён
- [x] **Проверено на ESP32:** `Auto-found packet: programs/program.enc`

### Песочница (продолжение)
- [x] Убран `object_factory.py` (`exec()` без песочницы, не использовался)
- [ ] Доступ к GPIO только по разрешённым пинам

### `os.dupterm` (опционально)
- [ ] Захват вывода из скрипта (для логов) через `os.dupterm`
- [ ] Если не нужно — оставить `print` в консоль

### Расширенный `main.py` (когда появится потребность)
- [ ] `set_time(current_time)` — для проверки `expires`
- [ ] `run_from_bytes(packet)` — для сети
- [ ] `run_batch(paths)` — несколько пакетов
- [ ] `hot_swap(path)` — замена без перезагрузки
- [x] NVS — хранение `used_command_ids` между перезагрузками

### Тесты
- [ ] Запустить **все** тесты на реальном ESP32
- [ ] Тесты для `execution_engine` (расширить)

### Документация
- [ ] README — обновить статус TUR55 (сейчас описывает v2.0 со старой криптографией)
- [ ] README_RU — обновить
- [ ] CHANGELOG — записать всё сделанное
- [ ] `TUR55_COMPLIANCE.md` — таблица соответствия
- [ ] `PROJECT_HISTORY.md` — добавить Сессии 7, 8, 9
- [ ] `DECISIONS_LOG.md` — добавить решения (WDT, таймаут, print)
- [ ] `ERRORS_AND_SOLUTIONS.md` — добавить ошибки (WDT, stdout, MicroPython)
- [x] `NEXT_SESSION.md` — удалён (дублировал `TODO.md`)
- [ ] `BUILD_GCM_FIRMWARE.md` — обновить
- [ ] `FIRMWARE_WITH_UCRYPTOGRAPHY.md` — обновить

### Продакшн
- [ ] Аудит безопасности
- [ ] Стресс-тесты на ESP32
- [ ] Обработка ошибок (потеря питания, обрыв связи)

---

## Текущий статус

**Готово:** **~95%** TUR55/Bronze (Bronze закрыт)

| Раздел | Статус |
|---|---|
| **Раздел 3.4** — формат пакета | ✅ Работает end-to-end |
| **Раздел 4** — AES-256-GCM | ✅ NIST 3/3 |
| **Раздел 4** — ECDSA secp256k1 | ✅ Работает |
| **Раздел 4** — RSA-OAEP | ✅ Работает |
| **Раздел 4** — BLAKE2s | ✅ Работает |
| **Раздел 4** — eFuse | ⏳ Gold (не Bronze) |
| **Раздел 5** — command_id (NVS) | ✅ **ЗАКРЫТО** |
| **Раздел 5** — expires (NTP) | ✅ **ЗАКРЫТО** |
| **Раздел 6** — whitelist / таймаут / память | ✅ |
| **Delivery** — MQTT | ✅ |
| **Delivery** — physical (`programs/`) | ✅ |
| **Раздел 9** — Лог в UART | ✅ |

**Что сделано:**
- ✅ Кастомная прошивка MicroPython v1.24.1 + ESP-IDF v5.2.2
- ✅ GCM C-модуль
- ✅ ucryptography (RSA-OAEP, BLAKE2s)
- ✅ secp256k1 (Bitcoin Core)
- ✅ Формат пакета TUR55
- ✅ Интеграция `program_loader.py` (Заход 1)
- ✅ Replay protection + expires (Заход 2)
- ✅ Интеграция `execution_engine.py` (Вариант 1+2)
- ✅ TUR55 работает на ESP32 (совместимость с MicroPython)
- ✅ `main.py` — стандартный пайплайн (CPython + ESP32)
- ✅ NVS — `used_command_ids` переживает перезагрузку
- ✅ MQTT — приём пакетов TUR55 по сети (Delivery Layer)
- ✅ NTP — источник времени для `expires`
- ✅ Физическая доставка — `programs/program.enc` (офлайн)
- ✅ Лог в UART — `Logger` → stdout → UART0
- ✅ CPython-проверка — все тесты пройдены
- ✅ **TUR55/Bronze — закрыт полностью**

**Что осталось (для Gold):**
- eFuse для ключей (раздел 4 TUR55) — **Gold**
- Secure boot — **Gold**