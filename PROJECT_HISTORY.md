# PROJECT_HISTORY — полная история проекта ESP32_Python_FUEL

**Цель:** привести проект к стандарту TUR55/Bronze **без отклонений**.

**Дата начала работы:** 2026-10-09
**Дата последнего обновления:** 2026-10-14
**Текущий статус:** ~75% TUR55/Bronze

---

## Сессия 1 (2026-10-09) — Знакомство, диагностика

### Что делали
- Знакомство с проектом (README, CHANGELOG, код)
- Диагностика несоответствий TUR55
- Анализ песочницы (`execution_sandbox.py`)
- Решение: whitelist модулей

### Результаты
- Убраны из whitelist: `sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`
- Оставлены: `machine`, `time`, `math`, `struct`, `json`, `gc`
- Соответствие TUR55 раздел 6 — **достигнуто**

### Ключевые решения
- **Цель:** TUR55/Bronze без отклонений
- **Подход:** пошаговый, с проверкой каждого этапа

### Коммиты
**Нет** — работа локальная, закоммичено 10 октября (`2abf26b`)

---

## Сессия 2 (2026-10-10) — GCM Python → C-модуль, boot loop

### Что делали
- GCM на чистом Python (`gcm.py`)
- NIST SP 800-38D тесты
- Бенчмарк на CPython
- Перенос на ESP32 — **провал** (boot loop)
- Установка WSL + ESP-IDF
- Сборка кастомной прошивки с GCM C-модулем

### Результаты
- `gcm.py` — AES-256-GCM на Python: **NIST 3/3 на CPython**
- 10 KB = 57 мс encrypt + 57 мс decrypt
- **MicroPython v1.24.1 + ESP-IDF v5.2.2** — рабочая комбинация
- GCM C-модуль (`~/cmodules/gcm/modgcm.c`) на mbedTLS
- **NIST 3/3 на ESP32** ✅

### Ошибки
- **Boot loop** (`RTCWDT_RTC_RESET`)
  - **Причина:** заливали **один файл** (`micropython.bin`) на `0x1000`
  - **Решение:** заливать **три файла** — `bootloader.bin` @ `0x1000`, `partition-table.bin` @ `0x8000`, `micropython.bin` @ `0x10000`
- **ESP-IDF v5.1.2** — не в списке поддерживаемых
- **ESP-IDF v5.3.2** — требует MicroPython main (v1.30-preview)
- **`STATIC` не определён** → замена на `static`
- **`MP_DEFINE_CONST_FUN_OBJ_4` / `_5`** не существуют → `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN`

### Ключевые решения
- **Отказ от табличного GHASH** — не заработал
- **Рабочая комбинация:** MicroPython v1.24.1 + ESP-IDF v5.2.2
- **Формат заливки:** три файла, три адреса

### Коммиты
- `2abf26b` — GCM implementation + sandbox whitelist fix
- `848e8eb` — Update NEXT_SESSION
- `095b07d` — Add BUILD_GCM_FIRMWARE.md
- `b5516ec` — GCM works on ESP32 - NIST 3/3 passed

---

## Сессия 3 (2026-10-11) — ucryptography, secp256k1, пакет TUR55

### Что делали
- Интеграция `ucryptography` (Ed25519, BLAKE2s, RSA-OAEP, ECDSA)
- Обход 3DES через заглушки
- Обёртка `mp_obj_int_to_bytes`
- **Переход на secp256k1** (Bitcoin Core)
- Формат пакета TUR55 (`tur55_packet.py`)

### Результаты
- **RSA-OAEP работает** ✅
- **BLAKE2s работает** ✅
- **ECDSA SECP256R1 работает** ✅
- **Ed25519 — БАГ** на сообщениях >96 байт
- **secp256k1 работает** через `usecp256k1` ✅
- Формат пакета TUR55 написан (JWE-inspired)
- Подпись ECDSA secp256k1 (вместо Ed25519)
- Создан `gcm_adapter.py` — единый интерфейс

### Ошибки
- **`undefined reference to mbedtls_des3_*`** — DES удалён в ESP-IDF v5.0
  - **Решение:** заглушки `des3_stubs.c`
- **`mp_obj_int_to_bytes` не существует в v1.24.1**
  - **Решение:** обёртка
- **Ed25519 падает** на 100, 110, 120, 128+ байт
  - **Решение:** переход на secp256k1
- **Модуль называется `usecp256k1`**, а не `secp256k1`

### Ключевые решения
- **Отказ от Ed25519** → secp256k1
- **Точное соответствие TUR55** (secp256k1) — важно
- **Формат пакета:** HEADER + PUBKEY + SESSION_KEY + SCRIPT + SIGNATURE

### Коммиты
- `a6b99f9` — ucryptography integration
- `e6a4523` — TUR55 packet format with secp256k1
- `687f032` — Update TODO

---

## Сессия 4 (2026-10-12, утро) — Round-trip, knowledge base, docs

### Что делали
- Round-trip тест TUR55 — CPython → ESP32
- Создание базы знаний (PROJECT_HISTORY, ERRORS, DECISIONS)
- Обновление документации

### Результаты
- ✅ **Round-trip работает end-to-end**
- `build_packet_cpython.py` — генерация пакета на CPython
- `decrypt_packet_esp32.py` — расшифровка на ESP32
- **`embit` вместо `coincurve`** — совместим с `usecp256k1`
- ECDSA подписи совпадают (libsecp256k1-совместимо)
- Созданы: `PROJECT_HISTORY.md`, `ERRORS_AND_SOLUTIONS.md`, `DECISIONS_LOG.md`
- Обновлены: `BUILD_GCM_FIRMWARE.md`, `FIRMWARE_WITH_UCRYPTOGRAPHY.md`

### Ошибки
- **`coincurve` не ставится на Python 3.14**
  - **Решение:** `embit`
- **ECDSA подписи разные** (cryptography vs usecp256k1)
  - **Решение:** `embit` (libsecp256k1)
- **RSA decrypt падает**
  - **Причина:** старый ключ на ESP32
  - **Решение:** перезалить `esp32_private_key.json`

### Ключевые решения
- **`embit` для CPython** (совместим с ESP32)
- **Round-trip** — подтверждён

### Коммиты
- `ae85a04` — Add knowledge base
- `ae0e295` — Add TUR55 round-trip test
- `193eacb` — Fix TODO and PROJECT_HISTORY
- `c8aa534` — Update BUILD_GCM_FIRMWARE
- `cfe46da` — Update docs

---

## Сессия 5 (2026-10-12, день) — Заход 1: program_loader

### Что делали
- Переписали `program_loader.py` под `tur55_packet.parse_packet()`
- Валидация конверта TUR55 раздел 3.2
- Убрали мёртвый код

### Результаты
- `program_loader.py` — принимает конверт 3.2
- `load_program(packet_bytes)` — основной вход (transport-independent)
- `load_program_from_file(filepath)` — обёртка для файла
- Загрузка ключей в `__init__()` (RSA + executor pubkey)
- `validate_permissions` — из `execution.permissions`
- `validate_runtime_constraints` — из `execution`
- Кэш по `command_id`
- `tur55_packet.py` — добавлен embit для CPython
- `build_packet_cpython.py` — обновлён под конверт 3.2
- `test_program_loader.py` — тест на CPython: **пройден**

### Что удалено
- `validate_signature` — подпись проверяет `parse_packet`
- `verify_integrity` — целостность даёт GCM tag
- Импорты `CryptoManager`, `LightweightSecurity`

### Ключевые решения
- **`load_program` принимает байты**, не путь (transport-independent)
- **Конверт 3.2:** `tur55_version`, `command_id`, `device_id`, `source`, `execution`, `custom_data`
- **`execution`** содержит: `setup`, `loop_logic`, `functions`, `permissions`, `runtime_limit_ms`, `memory_limit_kb`

### Коммиты
- `5bb81f1` — Заход 1

---

## Сессия 6 (2026-10-12, вечер) — Заход 2: replay + expires

### Что делали
- Replay protection (`command_id`)
- Опциональная проверка `expires`
- Обновление `.gitignore`, `TODO.md`

### Результаты
- `validate_command_id` — FIFO на 100 записей
- `validate_expires` — опционально (только при `time_synced`)
- `set_time(current_time)` — API для синхронизации времени
- `used_command_ids` + `used_command_ids_set`
- `test_loader_replay.py` — тест на CPython: **пройден**
- `test_esp32.py` — тест на ESP32: **пройден**
  - Первый `load_program` → OK
  - Второй `load_program` → `Command replay detected` ✅
- `.gitignore` — убран `__pycache__` из отслеживания

### Ключевые решения
- **`used_command_ids` в RAM** — позже перенести в NVS
- **`expires` опционально** — проверяется только при `time_synced`
- **Раздел 5 TUR55** — **закрыт**

### Коммиты
- `3732875` — Заход 2
- `fbe5e71` — Убрать __pycache__
- `32f1141`, `055a96b`, `11dabf5`, `7611296` — TODO

---

## Сессия 7 (2026-10-13) — execution_engine под конверт 3.2

### Что делали
- Интегрировали `execution_engine.py` с новым `program_loader`
- `execute_program` — принимает конверт 3.2
- Setup-контекст → loop (merged)
- `hot_swap` — под конверт 3.2
- Лимиты из пакета

### Результаты
- `execute_program(program_data)` — конверт 3.2
- Раскладка `execution.functions` + `execution.setup` + `execution.loop_logic`
- `merged = globals + locals` — setup-переменные видны в loop
- `hot_swap(new_program)` — по `command_id`
- Лимиты из пакета: `memory_limit_kb`, `runtime_limit_ms` — применяются к sandbox
- Восстановление лимитов в `finally`
- `build_test_packet_cpython.py` — генератор тестовых пакетов
- `test_engine_cpython.py` — тест на CPython: **пройден**

### Ключевые решения
- **`execute_program` принимает конверт 3.2**, не плоский `{setup, loop_logic}`
- **Setup-контекст через `merged`** — CPython и MicroPython различаются в поведении `exec`
- **Лимиты из пакета** — применяются на время выполнения, потом восстанавливаются

### Коммиты
- `9928ef3` — execute_program под конверт 3.2
- `7e030fa` — setup → loop (merged)
- `e2c214d` — Тесты engine
- `4ffeb9d` — hot_swap под конверт 3.2
- `f54a825` — Лимиты из конверта

---

## Сессия 8 (2026-10-14, день) — TUR55 на ESP32 + main.py

### Что делали
- Отладка `execution_engine` на ESP32
- Обход ограничений MicroPython
- `main.py` — стандартный пайплайн

### Результаты
- **TUR55 работает end-to-end на ESP32** ✅
- `main.py` — стандартный пайплайн (`parse + validate + execute`)
- `main.py` прошёл на CPython (156 мс) и ESP32 (227 мс)

### Ошибки MicroPython
- **`NameError: name 'vars' isn't defined`**
  - **Решение:** `except (ImportError, NameError)`
- **`NameError: name '__builtins__' isn't defined`**
  - **Решение:** fallback на пустой dict
- **`NameError: name 'TimeoutError' isn't defined`**
  - **Решение:** заменён на `RuntimeError`
- **`AttributeError: 'module' object has no attribute 'stdout'`**
  - **Причина:** в MicroPython `sys.stdout` отсутствует и не переопределяется
  - **Решение:** убрана подмена `sys.stdout`
- **WDT-сбросы после теста**
  - **Причина:** `machine.WDT.deinit()` не работает в MicroPython
  - **Решение:** WDT убран, кооперативный таймаут через `machine.Timer(-1)`
- **`print` не перехватывается** через `__builtins__`
  - **Решение:** отказались от перехвата (в MicroPython невозможно)
- **`test_esp32.py` зависал**
  - **Причина:** MicroPico теряет связь на длинных операциях
  - **Решение:** использовать miniterm или пошаговый ввод

### Ключевые решения
- **WDT не используется** — неостановим в MicroPython
- **Кооперативный таймаут** через `machine.Timer` + флаги
- **`print` не перехватывается** — идёт в консоль
- **`set_time` не включён** в `main.py` — нет источника времени
- **Стандартный `main.py`** — 100 строк, без `set_time`
- **Расширения** — перечислены в docstring, добавятся потом

### Коммиты
- `25676ce` — execution_engine + sandbox на ESP32
- `9559c41` — main.py

---

## Сессия 9 (2026-10-14, вечер) — Чистка мёртвого кода

### Что делали
- Удаление мёртвого кода v2.0
- Обновление `TODO.md`

### Что удалено (18 файлов, ~130 KB, ~2900 строк)

**v2.0 криптография:**
- `crypto_manager.py` (AES-CTR + HMAC) — заменён на GCM
- `lightweight_security.py` (HMAC-SHA256) — заменён на ECDSA

**v2.0 JSON:**
- `fast_json_loader.py` — заменён на `program_loader`

**v2.0 тесты/бенчмарки:**
- `performance_tests.py`, `run_tests.py`
- `tests/test_crypto_manager.py`, `tests/test_lightweight_security.py`

**v2.0 дыры:**
- `object_factory.py` — `exec()` без песочницы

**Дубли GCM:**
- `gcm_esp32.py` — заменён на `gcm_adapter`

**Устаревшее:**
- `line_compiler.py` — старый компилятор
- `decrypt_packet_esp32.py` — заменён `test_engine_esp32`
- `bench_gcm.py` — не используется
- `test_ed25519_size.py` — Ed25519 отменён

### Результаты
- **Проект чистый** — только актуальные модули
- 21 `.py` файл в корне

### Коммиты
- `f79fd61` — crypto_manager, lightweight_security
- `cd7f677` — fast_json_loader, performance_tests, run_tests, тесты
- `bc09b7e` — object_factory
- `8028b9a` — line_compiler, decrypt_packet_esp32, bench_gcm, gcm_esp32, test_ed25519_size

---

## Общая хронология ключевых решений

| Дата | Решение | Почему |
|---|---|---|
| 2026-10-09 | Цель — TUR55/Bronze | Запрос пользователя |
| 2026-10-10 | GCM на Python → C-модуль | GCM недоступен в MicroPython |
| 2026-10-10 | ESP-IDF v5.2.2 | Единственная рабочая версия |
| 2026-10-10 | MicroPython v1.24.1 | Стабильный, поддерживает v5.2.2 |
| 2026-10-10 | Заливка трёх файлов | Решение boot loop |
| 2026-10-11 | ucryptography | RSA-OAEP, BLAKE2s, ECDSA |
| 2026-10-11 | Заглушки 3DES | DES удалён в ESP-IDF v5.0 |
| 2026-10-11 | secp256k1 (Bitcoin Core) | Ed25519 сломан, TUR55 требует secp256k1 |
| 2026-10-11 | Формат пакета TUR55 | JWE-inspired |
| 2026-10-12 | embit для CPython | coincurve не ставится |
| 2026-10-12 | Round-trip TUR55 | Подтверждение формата |
| 2026-10-12 | Заход 1: program_loader | Конверт 3.2, transport-independent |
| 2026-10-12 | Заход 2: replay + expires | Раздел 5 TUR55 закрыт |
| 2026-10-13 | execute_program под конверт 3.2 | Интеграция с program_loader |
| 2026-10-13 | Setup → loop (merged) | CPython/MicroPython различаются |
| 2026-10-13 | Лимиты из пакета | TUR55 требует соблюдения лимитов |
| 2026-10-14 | WDT убран | Неостановим в MicroPython |
| 2026-10-14 | Кооперативный таймаут | Замена WDT |
| 2026-10-14 | `sys.stdout` / `print` не перехватываются | Невозможно в MicroPython |
| 2026-10-14 | main.py — стандартный пайплайн | Одна точка входа |
| 2026-10-14 | Удалить мёртвый код v2.0 | Чистота проекта |

---

## Текущий статус

**~75% TUR55/Bronze**

| Раздел | Статус |
|---|---|
| 3.4 — формат пакета | ✅ Работает end-to-end |
| 4 — AES-256-GCM | ✅ NIST 3/3 |
| 4 — ECDSA secp256k1 | ✅ Работает |
| 4 — RSA-OAEP | ✅ Работает |
| 4 — BLAKE2s | ✅ Работает |
| 4 — eFuse | ❌ |
| 5 — expires / command_id | ✅ **ЗАКРЫТО** |
| 6 — whitelist / таймаут / память | ✅ |

**Что сделано:**
- ✅ Кастомная прошивка MicroPython v1.24.1 + ESP-IDF v5.2.2
- ✅ GCM C-модуль
- ✅ ucryptography (RSA-OAEP, BLAKE2s)
- ✅ secp256k1 (Bitcoin Core)
- ✅ Формат пакета TUR55
- ✅ `program_loader` под конверт 3.2 (Заход 1)
- ✅ Replay protection + expires (Заход 2)
- ✅ `execution_engine` под конверт 3.2
- ✅ TUR55 работает на ESP32
- ✅ `main.py` — стандартный пайплайн
- ✅ Проект очищен от мёртвого кода

**Что осталось:**
1. **eFuse** для ключей (раздел 4 TUR55)
2. **MQTT** — сетевой слой
3. **Физическая доставка** — `programs/program.enc`
4. **Документация** — README, CHANGELOG, TUR55_COMPLIANCE
5. **Расширения `main.py`** — `set_time`, `run_from_bytes`, `run_batch`, `hot_swap`