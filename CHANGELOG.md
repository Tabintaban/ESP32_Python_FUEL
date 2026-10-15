# Changelog

All notable changes to the ESP32_Python_FUEL project will be documented in this file.

Проект реализует **Execution Layer (Layer 4)** стандарта **TUR55/Bronze** — безопасное выполнение программ на ESP32 через MicroPython.

---

## [3.2.1] — 2026-10-16 — Физическая доставка

**Статус:** ~87% TUR55/Bronze

### Added

- **Физическая доставка** (TUR55 тезис 8) — `programs/program.enc`
  - Папка `programs/` на ESP32 (офлайн-доставка)
  - `main._find_packet()` — ищет `programs/program.enc`, потом `test_packet_engine.bin`
  - `programs/*.enc` — в `.gitignore` (пакет секретный)
  - `programs/readme.md` — обновлён (назначение папки)

### Changed

- **`main.py`** — `run_program(packet_path=None)` — автопоиск пакета
- **`main.py`** — `has_network` (NTP только на ESP32, на CPython — skip без ошибки)
- **`.gitignore`** — добавлен `programs/*.enc`
- **`programs/readme.md`** — обновлён

### Fixed

- **NTP на CPython** — `NTP skipped (no network module)` вместо `NTP sync error`

### Проверено на ESP32

- Папка `programs/` создана: `os.mkdir('programs')`
- `program.enc` залит через `mpremote fs cp`
- `main.main()` → `Auto-found packet: programs/program.enc`
- Пайплайн выполнен успешно

### Коммиты

- `888717b` — Физическая доставка: programs/program.enc
- `2465438` — PROJECT_HISTORY: физическая доставка
- `e1ecbba` — DECISIONS_LOG: Решение 26

---

## [3.2.0] — 2026-10-15 — MQTT + NTP

**Статус:** ~85% TUR55/Bronze

### Added

- **MQTT** (Delivery Layer TUR55) — `mqtt_client.py`, `mqtt_publisher.py`
  - `MQTTReceiver` — приём пакетов (umqtt.simple)
  - `MQTTPublisher` — отправка (paho-mqtt)
  - Wi-Fi подключение (`network.WLAN`)
  - Топик: `tur55/device/esp32_001`
  - Брокер: `broker.hivemq.com`
- **NTP** — `time_sync.py`
  - `sync_time(ssid, password)` — синхронизация через NTP
  - `EPOCH_OFFSET = 946684800` (MicroPython → Unix)
- **`main.py`** — NTP-интеграция
  - Опциональный вызов `sync_time`
  - `wifi_ssid`, `wifi_password` из `secrets.py`
- **`secrets.py`** — Wi-Fi + MQTT настройки (в `.gitignore`)

### Changed

- **`main.py`** — `run_program` принимает `wifi_ssid`, `wifi_password`
- **`main()`** — читает из `secrets.py` (fallback на `ImportError`)
- **`build_test_packet_cpython.py`** — `expires` в JSON (+3600 / -3600)
- **`.gitignore`** — добавлен `secrets.py`

### Fixed

- **`expires` проверяется** — NTP даёт точное время
- **Fallback на CPython** — `NTP skipped`, работает без NTP

### Проверено на ESP32

- **MQTT end-to-end:** CPython → MQTT → ESP32 (862 байта)
- **NTP:** `Time synced: 1792057463`
- **`expires`:** +3600 → принят, -3600 → `Command expired`
- **Replay:** второй запуск → `Command replay detected` (NVS)

### Коммиты

- `07f1739` — MQTT: mqtt_client + mqtt_publisher
- `86b1c4d` — TODO: MQTT (~80%)
- `b2750fa` — TUR55_COMPLIANCE: MQTT (~80%)
- `6c2c910` — NTP: time_sync.py + expires в build_test_packet
- `afabe77` — main.py: NTP-интеграция
- `cf8c83f` — README_RU: форматирование markdown

---

## [3.1.0] — 2026-10-15 — NVS для `used_command_ids`

**Статус:** ~78% TUR55/Bronze

### Added

- **NVS-хранилище** для `used_command_ids`
  - `program_loader._load_used_command_ids()` — загрузка из NVS при старте
  - `program_loader._save_used_command_ids()` — сохранение при новом `command_id`
  - Namespace: `tur55_replay`
  - Ключ: `used_ids` (JSON-список)
  - `nvs.commit()` — обязательно для сохранения

### Changed

- **`program_loader.validate_command_id()`** — вызывает `_save_used_command_ids()`
- **Раздел 5 TUR55** — replay protection **полностью закрыт** (RAM → NVS)
- **Статус:** ~75% → **~78%**

### Fixed

- **Replay protection переживает перезагрузку** — раньше `used_command_ids` терялись при Ctrl+D
- **Fallback на RAM** — CPython работает как раньше

### Проверено на ESP32

- Первый запуск → OK
- Второй запуск → `Command replay detected` (RAM)
- Ctrl+D → `Command replay detected` (NVS)

### Коммиты

- `bc9f29c` — program_loader: NVS
- `5e2a5c2` — TODO + TUR55_COMPLIANCE: NVS (~78%)
- `b67321b` — PROJECT_HISTORY: Сессия 10
- `74a1473` — DECISIONS_LOG: Решение 24

---

## [3.0.0] — 2026-10-14 — TUR55/Bronze

**Статус:** ~75% TUR55/Bronze

**Главная победа:** пайплайн TUR55 работает end-to-end на ESP32.

### Added

#### Криптография (TUR55 раздел 4)
- **GCM C-модуль** (`~/cmodules/gcm/modgcm.c`) на mbedTLS
  - `gcm.encrypt(key, iv, pt, aad)` → `(ct, tag)`
  - `gcm.decrypt(key, iv, ct, tag, aad)` → `pt`
  - NIST SP 800-38D: **3/3 на ESP32**
- **ucryptography** — RSA-OAEP, BLAKE2s
- **secp256k1** (`usecp256k1` из Bitcoin Core) — ECDSA sign/verify
- **embit** для CPython (совместим с `usecp256k1`)
- `gcm_adapter.py` — единый интерфейс (ESP32: C-модуль, CPython: `gcm.py`)

#### Формат пакета TUR55 (раздел 3.4)
- `tur55_packet.py` — JWE-inspired binary
- Структура: `HEADER + PUBKEY + SESSION_KEY + SCRIPT + SIGNATURE`
- `build_packet()` — для экзекутора
- `parse_packet()` — для ESP32
- `build_packet_cpython.py` — генератор пакетов на CPython

#### Конверт TUR55 (раздел 3.2)
- Поля: `tur55_version`, `command_id`, `device_id`, `source`, `execution`, `custom_data`
- `execution` содержит: `setup`, `loop_logic`, `functions`, `permissions`, `runtime_limit_ms`, `memory_limit_kb`, `expires`

#### `program_loader.py` (Заход 1)
- Переписан под `tur55_packet.parse_packet()`
- `load_program(packet_bytes)` — transport-independent вход
- `load_program_from_file(filepath)` — обёртка
- Валидация конверта 3.2
- Загрузка ключей в `__init__()`
- Кэш по `command_id`

#### Replay protection + expires (Заход 2, TUR55 раздел 5)
- `validate_command_id` — FIFO на 100 записей
- `validate_expires` — опционально (только при `time_synced`)
- `set_time(current_time)` — API для синхронизации времени

#### `execution_engine.py`
- `execute_program(program_data)` — принимает конверт 3.2
- Setup-контекст передаётся в loop (`merged` globals + locals)
- `hot_swap(new_program)` — под конверт 3.2
- Лимиты из пакета применяются к sandbox, восстанавливаются в `finally`

#### `main.py`
- Стандартный пайплайн (`parse + validate + execute`)
- `Logger` (5 уровней)
- `run_program(path, max_iterations, log_level)`
- Работает на CPython и ESP32

#### Документация
- `PROJECT_HISTORY.md` — 9 сессий
- `DECISIONS_LOG.md` — 23 решения
- `ERRORS_AND_SOLUTIONS.md` — 28 ошибок
- `TODO.md` — актуальный план
- `TUR55_COMPLIANCE.md` — таблица соответствия

### Changed

- **`execution_engine.py`** — `execute_program` принимает конверт 3.2 (вместо плоского `{setup, loop_logic}`)
- **`execution_engine.py`** — setup-контекст через `merged` (CPython и MicroPython различаются)
- **`execution_engine.py`** — лимиты из пакета (TUR55 требует соблюдения)
- **`execution_sandbox.py`** — WDT убран (неостановим в MicroPython)
- **`execution_sandbox.py`** — кооперативный таймаут через `machine.Timer(-1)`
- **`execution_sandbox.py`** — `sys.stdout` / `print` не перехватываются
- **`tur55_packet.py`** — embit для CPython (`_ecdsa_sign`, `_ecdsa_verify`)
- **`main.py`** — переписан целиком под TUR55
- **`.gitignore`** — обновлён (`__pycache__`, `*.pyc`, `esp32_private_key.*`)

### Removed (мёртвый код v2.0, 18 файлов, ~130 KB, ~2900 строк)

#### v2.0 криптография
- `crypto_manager.py` — AES-CTR + HMAC (заменён на GCM)
- `lightweight_security.py` — HMAC (заменён на ECDSA)

#### v2.0 JSON
- `fast_json_loader.py` — заменён на `program_loader`

#### v2.0 тесты/бенчмарки
- `performance_tests.py`, `run_tests.py`
- `tests/test_crypto_manager.py`, `tests/test_lightweight_security.py`

#### v2.0 дыры
- `object_factory.py` — `exec()` без песочницы

#### Дубли GCM
- `gcm_esp32.py` — заменён на `gcm_adapter`

#### Устаревшее
- `line_compiler.py`, `decrypt_packet_esp32.py`, `bench_gcm.py`, `test_ed25519_size.py`

#### Документация
- `NEXT_SESSION.md` — дублировал `TODO.md`

### Fixed (совместимость с MicroPython)

- `vars()` isn't defined → `except (ImportError, NameError)`
- `__builtins__` isn't defined → `try/except NameError` + `globals()` fallback
- `TimeoutError` isn't defined → заменён на `RuntimeError`
- `'module' object has no attribute 'stdout'` → убрана подмена `sys.stdout`
- `print` не перехватывается через `__builtins__` → отказались от перехвата
- WDT-сбросы после теста → WDT убран, кооперативный таймаут
- Boot loop (`RTCWDT_RTC_RESET`) → заливка трёх файлов по трём адресам

### Tests

- `test_program_loader.py` — ProgramLoader (CPython)
- `test_loader_replay.py` — replay + expires
- `test_engine_cpython.py` — engine (CPython)
- `test_engine_esp32.py` — engine (ESP32)
- `test_esp32.py` — ProgramLoader (ESP32)
- `test_tur55_packet.py`, `test_tur55_packet_esp32.py`
- `test_gcm.py`, `test_gcm_esp32.py`, `test_hash.py`, `test_rsa_esp32.py`

### Известные ограничения

- **eFuse** — не реализован (раздел 4 TUR55)
- **Кооперативный таймаут** — не прерывает зависший C-код (hard-guarantee отсутствует)
- **`used_command_ids` в RAM** — теряется при перезагрузке (**исправлено в v3.1.0**)
- **MQTT / сетевой стек** — не реализованы (**исправлено в v3.2.0**)
- **`expires` не проверяется** — нет источника времени (**исправлено в v3.2.0**)
- **Физическая доставка** — не реализована (**исправлено в v3.2.1**)
- **`os.dupterm`** — не используется (нет перехвата `print`)

---

## [2.0.0] — 2026-07-12 — Устранение уязвимостей (УСТАРЕЛО)

> **Примечание:** Эта версия полностью заменена на v3.0.0 (TUR55/Bronze).
> Файлы, описанные здесь, **удалены** из проекта.

### Security Fixes

- **`crypto_manager.py`** — заменён на AES-CTR + HMAC-SHA256 (позже заменён на GCM)
- **`lightweight_security.py`** — заменён на HMAC-SHA256 (позже заменён на ECDSA)
- **`execution_sandbox.py`** — SafeImporter с whitelist модулей
- **`execution_engine.py`** — таймаут через `_thread`
- **`memory_optimizer.py`** — pre/during/after checks
- **`fast_json_loader.py`** — сохранение newline
- **`line_compiler.py`** — безопасная нормализация отступов
- **`main.py`** — `Logger` с уровнями

---

## [1.0.0] — 2026-01-23 — Initial Release

### Features

- AES-GCM шифрование JSON-файлов
- Проверка подписей
- Изолированное выполнение в песочнице
- Быстрая загрузка JSON
- Оптимизация памяти для ESP32
- Hot-reload
- Бенчмарки (< 500 мс)

---

## Ссылки

- **TUR55 Standard:** https://github.com/Tabintaban/Protocol_TUR55
- **ESP32_Python_FUEL:** https://github.com/Tabintaban/ESP32_Python_FUEL
- **MicroPython v1.24.1:** https://github.com/micropython/micropython/releases/tag/v1.24.1
- **ESP-IDF v5.2.2:** https://github.com/espressif/esp-idf/tree/v5.2.2
- **NIST SP 800-38D:** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf