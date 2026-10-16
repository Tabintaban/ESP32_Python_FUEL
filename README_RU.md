
# ESP32_Python_FUEL

**Secure Execution Layer (Layer 4) стандарта TUR55.**
Безопасное выполнение программ на ESP32 через MicroPython с шифрованием, строгими лимитами ресурсов и изолированной средой исполнения.

[![Status](https://img.shields.io/badge/TUR55--Bronze-95%25-brightgreen)]()
[![MicroPython](https://img.shields.io/badge/MicroPython-v1.24.1-blue)]()
[![ESP--IDF](https://img.shields.io/badge/ESP--IDF-v5.2.2-blue)]()

---

## Что такое TUR55?

**TUR55 (Trust Unified Regulation)** — открытый стандарт для выполнения блокчейн-команд на IoT-устройствах. Blockchain-agnostic, transport-independent, с изолированным исполнением.

**Автор стандарта:** NOMOS-H
**Дата фиксации:** 2026-04-10
**Репозиторий:** https://github.com/Tabintaban/Protocol_TUR55

### Четыре слоя архитектуры

| Слой | Назначение |
|---|---|
| **Event Layer** | Триггер из смарт-контракта |
| **Executor Layer** | Формирует зашифрованный пакет |
| **Delivery Layer** | Доставка (MQTT, HTTP, BLE, LoRaWAN, QR) |
| **Execution Layer** | Песочница, где скрипт безопасно исполняется |

**ESP32_Python_FUEL реализует `Layer 4 — Execution Layer`.**

---

## Статус

**~95% TUR55/Bronze — Bronze закрыт.**

| Раздел | Статус |
|---|---|
| 3.2 — конверт TUR55 | ✅ |
| 3.4 — формат пакета | ✅ работает end-to-end |
| 4 — AES-256-GCM | ✅ NIST 3/3 на ESP32 |
| 4 — ECDSA secp256k1 | ✅ |
| 4 — RSA-OAEP | ✅ |
| 4 — BLAKE2s | ✅ |
| 4 — eFuse | ⏳ Gold (не Bronze) |
| 5 — `command_id` (replay) | ✅ NVS |
| 5 — `expires` | ✅ NTP |
| 6 — whitelist / таймаут / память | ✅ |
| Delivery — MQTT + physical | ✅ |
| 9 — Лог в UART | ✅ |

**TUR55/Bronze — закрыт полностью.**
**Пайплайн работает end-to-end на CPython и ESP32.**

Полная таблица соответствия — в [TUR55_COMPLIANCE.md](TUR55_COMPLIANCE.md).

---

## Архитектура

### Пайплайн

```
Пакет TUR55 (bytes)
    │
    ▼
parse_packet()             ── ECDSA verify + RSA-OAEP decrypt + AES-GCM decrypt
    │
    ▼
validate envelope 3.2      ── program_loader
    │
    ▼
validate permissions       ── execution.permissions
validate runtime limits    ── runtime_limit_ms, memory_limit_kb
validate expires           ── опционально (при time_synced)
validate command_id        ── replay protection (FIFO 100)
    │
    ▼
execute_program()          ── execution_engine
    │
    ├─ setup (functions + setup lines)
    └─ loop (loop_logic lines)
    │
    ▼
sandbox                    ── execution_sandbox (whitelist + кооперативный таймаут)
```

### Модули

| Модуль | Назначение |
|---|---|
| `main.py` | Точка входа — стандартный пайплайн |
| `program_loader.py` | Parse + validate конверта TUR55 |
| `execution_engine.py` | Setup + loop execution |
| `execution_sandbox.py` | Песочница (whitelist, таймаут, память) |
| `tur55_packet.py` | Формат пакета TUR55 (build + parse) |
| `gcm_adapter.py` | Единый интерфейс GCM |
| `gcm.py` | GCM на чистом Python (fallback для CPython) |
| `memory_optimizer.py` | Управление памятью |
| `mqtt_client.py` | Приём MQTT (ESP32) |
| `time_sync.py` | NTP-синхронизация (ESP32) |

---

## Криптография

| Алгоритм | Назначение | Реализация |
|---|---|---|
| **AES-256-GCM** | Симметричное шифрование | C-модуль на mbedTLS |
| **ECDSA secp256k1** | Подпись | `usecp256k1` (Bitcoin Core) |
| **RSA-OAEP** | Шифрование сессионного ключа | `ucryptography` |
| **BLAKE2s** | Хэширование | `ucryptography` |

**Соответствие:** AES-256-GCM прошёл **NIST SP 800-38D** тесты (3/3) на ESP32.

**Совместимость с CPython:** `embit` (libsecp256k1-совместимый) для подписей.

---

## Требования

| Компонент | Версия | Почему |
|---|---|---|
| **MicroPython** | **v1.24.1** | Стабильный релиз |
| **ESP-IDF** | **v5.2.2** | Совместим с v1.24.1 |
| **ESP32** | ESP32-D0WDQ6-V3 (WROOM) | Без PSRAM |
| **Python (WSL)** | 3.10.12 | Требование ESP-IDF |

**ESP-IDF v5.1.2 и v5.3.2 — НЕ подходят.**

---

## Быстрый старт

### 1. Сборка кастомной прошивки

Полная инструкция — в [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md).

**Кратко:**

```bash
# Активировать ESP-IDF
. ~/esp/esp-idf-v5.2.2/export.sh

# Собрать MicroPython с C-модулями
cd ~/micropython/ports/esp32
rm -rf build-ESP32_GENERIC
make BOARD=ESP32_GENERIC USER_C_MODULES=/home/tavintavan/cmodules/micropython.cmake
```

### 2. Заливка на ESP32

**Три файла, три адреса:**

| Файл | Адрес |
|---|---|
| `bootloader.bin` | `0x1000` |
| `partition-table.bin` | `0x8000` |
| `micropython.bin` | `0x10000` |

```powershell
py -m esptool --chip esp32 --port COM3 --baud 460800 write-flash --flash-mode dio --flash-size 4MB --flash-freq 40m -z 0x1000 "bootloader.bin" 0x8000 "partition-table.bin" 0x10000 "micropython.bin"
```

**ВНИМАНИЕ:** НЕ заливать `micropython.bin` по адресу `0x1000` — это причина boot loop.

### 3. Загрузка модулей на ESP32

Через MicroPico или `mpremote`:

```
main.py
program_loader.py
execution_engine.py
execution_sandbox.py
tur55_packet.py
gcm_adapter.py
memory_optimizer.py
test_packet_engine.bin
esp32_private_key.json
executor_pubkey.bin
```

### 4. Запуск

```python
import main
main.main()
```

**Ожидаемый вывод:**

```
[INFO] === TUR55 Pipeline ===
[INFO] Init ProgramLoader...
[INFO] Init ExecutionEngine...
[INFO] Loading packet: test_packet_engine.bin
[INFO] command_id: 0xtest_engine_001
[INFO] permissions: ['time', 'math']
[INFO] runtime_limit_ms: 5000
[INFO] memory_limit_kb:  25
[INFO] Executing program (max_iterations=5)...
setup done, x = 42
loop iter 0 x = 42
...
[INFO] setup success:    True
[INFO] loop iterations:  5
[INFO] === Done ===
```

---

## Формат конверта TUR55 (раздел 3.2)

```json
{
  "tur55_version": "1.0",
  "command_id": "0x7e5f8a3c",
  "device_id": "esp32_001",
  "source": {
    "smart_contract": "0x1234",
    "transaction_hash": "0xabcd",
    "block_number": 12345678
  },
  "execution": {
    "user_wallet": "0xUserWallet",
    "amount": 50.5,
    "expires": 1741500000,
    "runtime_limit_ms": 5000,
    "memory_limit_kb": 25,
    "permissions": ["gpio", "time"],
    "functions": [],
    "setup": ["led = machine.Pin(2, machine.Pin.OUT)"],
    "loop_logic": ["led.value(1)", "time.sleep(0.5)"]
  },
  "custom_data": {
    "action": "unlock",
    "duration": 30
  }
}
```

---

## Формат пакета TUR55 (раздел 3.4)

**Бинарный, JWE-inspired:**

```
HEADER       8 байт   (magic "TUR5", version, flags)
PUBKEY       1 + 33   (compressed secp256k1)
SESSION_KEY  2 + ~256 (RSA-OAEP encrypted)
SCRIPT       12 + 4 + N + 16  (iv + length + ct + tag)
SIGNATURE    2 + M    (DER-encoded ECDSA secp256k1)
```

**Подпись покрывает:** `HEADER + PUBKEY + SESSION_KEY + SCRIPT`
**AAD для GCM:** `HEADER + PUBKEY + SESSION_KEY`

### Сборка пакета (сторона экзекутора)

```python
import build_packet_cpython

packet = build_packet_cpython.build_packet(
    json_data=my_envelope,
    esp32_public_key=rsa_pubkey,
    executor_sk=ecdsa_secret,
    executor_pubkey=ecdsa_pubkey_bytes
)
```

---

## Безопасность

| Мера | Реализация |
|---|---|
| Шифрование | AES-256-GCM (NIST 3/3) |
| Подпись | ECDSA secp256k1 |
| Обмен ключами | RSA-OAEP |
| Replay protection | `command_id` FIFO (100) |
| Песочница | `SafeImporter` с whitelist |
| Запрещённые builtins | `eval`, `exec`, `compile`, `open`, `getattr` |
| Таймаут | Кооперативный (`machine.Timer`) |
| Лимит памяти | `_check_memory_usage` |
| Лимиты из пакета | `limit_resources` |

### Разрешённые модули в песочнице

`machine`, `time`, `math`, `struct`, `json`, `gc`

### Запрещённые модули

`sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`

---

## Документация

| Файл | Назначение |
|---|---|
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | Полная история (12 сессий) |
| [DECISIONS_LOG.md](DECISIONS_LOG.md) | 26 ключевых решений |
| [ERRORS_AND_SOLUTIONS.md](ERRORS_AND_SOLUTIONS.md) | 28 ошибок и решений |
| [TODO.md](TODO.md) | Актуальный план |
| [TUR55_COMPLIANCE.md](TUR55_COMPLIANCE.md) | Таблица соответствия |
| [CHANGELOG.md](CHANGELOG.md) | История версий |
| [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md) | Сборка прошивки |
| [FIRMWARE_WITH_UCRYPTOGRAPHY.md](FIRMWARE_WITH_UCRYPTOGRAPHY.md) | Детали ucryptography |

---

## Известные ограничения (для Gold)

1. **eFuse** не реализован — **Gold уровень** (не Bronze). Ключи в `esp32_private_key.json`.
2. **Secure boot** — **Gold уровень**.
3. **Кооперативный таймаут** — не прерывает зависший C-код. Hard-guarantee отсутствует.
4. **`used_command_ids` в NVS** — сохраняется между перезагрузками. ✅
5. **`expires` проверяется** — через NTP. ✅
6. **MQTT / сетевой стек** — реализованы. ✅
7. **Физическая доставка** (`programs/program.enc`) — реализована. ✅
8. **Лог в UART** — реализован (Logger → stdout → UART0). ✅

---

## Тестирование

| Тест | Платформа | Назначение |
|---|---|---|
| `test_program_loader.py` | CPython | ProgramLoader |
| `test_loader_replay.py` | CPython | Replay + expires (4/4) |
| `test_engine_cpython.py` | CPython | Engine |
| `test_gcm.py` | CPython | GCM (NIST 3/3) |
| `tests/` (pytest) | CPython | Sandbox, Engine, Memory (5/5) |
| `test_engine_esp32.py` | ESP32 | Engine (железо) |
| `test_esp32.py` | ESP32 | ProgramLoader (железо) |
| `test_tur55_packet_esp32.py` | ESP32 | Формат пакета (железо) |
| `test_gcm_esp32.py` | ESP32 | GCM (C-модуль) |
| `test_rsa_esp32.py` | ESP32 | RSA-OAEP (железо) |

---

## Структура проекта

```
ESP32_Python_FUEL/
│
├── main.py                                              # Entry point — standard pipeline
├── program_loader.py                                    # Parse + validate TUR55 envelope
├── execution_engine.py                                  # Setup + loop execution
├── execution_sandbox.py                                 # Sandbox (whitelist, timeout, memory)
├── tur55_packet.py                                      # TUR55 packet format (build + parse)
├── gcm_adapter.py                                       # Unified GCM interface
├── gcm.py                                               # Pure Python GCM (CPython fallback)
├── memory_optimizer.py                                  # Memory management
├── mqtt_client.py                                       # MQTT receiver (ESP32)
├── time_sync.py                                         # NTP time sync (ESP32)
│
├── build_packet_cpython.py                              # Packet builder (executor side)
├── build_test_packet_cpython.py                         # Test packet builder
├── mqtt_publisher.py                                    # MQTT publisher (CPython)
│
├── test_program_loader.py                               # ProgramLoader (CPython)
├── test_loader_replay.py                                # Replay + expires (CPython)
├── test_engine_cpython.py                               # Engine (CPython)
├── test_engine_esp32.py                                 # Engine (ESP32)
├── test_esp32.py                                        # ProgramLoader (ESP32)
├── test_tur55_packet_esp32.py                           # Packet (ESP32)
├── test_gcm.py                                          # GCM (CPython)
├── test_gcm_esp32.py                                    # GCM (ESP32)
├── test_rsa_esp32.py                                    # RSA-OAEP (ESP32)
│
├── tests/                                               # Unit tests (pytest-style)
│ ├── __init__.py
│ ├── test_execution_engine.py
│ ├── test_execution_sandbox.py
│ └── test_memory_optimizer.py
│
├── patches/ucryptography/                               # ucryptography patches                                    
│ ├── des3_stubs.c                                       # 3DES stubs (DES was removed in ESP-IDF v5.0)
│ ├── micropython.cmake                                  # Integration of ucryptography into the MicroPython build
│ └── modcryptography.c                                  # Patch for mp_obj_int_to_bytes (wrapper for v1.24.1)
│
├── programs/                                            # Offline packets (TUR55 physical delivery)
│ └── readme.md
├── data/                                                # Decrypted HTML/CSS/JS (future)
│ └── readme.md
├── utils/                                               # Utilities
│ └── readme.md
├── .vscode/                                             # VS Code settings
│ └── settings.json
│
├── PROJECT_HISTORY.md                                   # 12 sessions
├── DECISIONS_LOG.md                                     # 26 decisions
├── ERRORS_AND_SOLUTIONS.md                              # 28 errors
├── TODO.md                                              # Current plan (Bronze closed)
├── TUR55_COMPLIANCE.md                                  # Compliance table (~95% Bronze)
├── CHANGELOG.md                                         # v3.3.0
├── BUILD_GCM_FIRMWARE.md                                # Firmware build
├── FIRMWARE_WITH_UCRYPTOGRAPHY.md                       # ucryptography details
├── README.md                                            # This file
├── README_RU.md                                         # Russian version
├── LICENSE.md                                           # MIT
└── .gitignore
```

**Runtime artifacts (gitignored):**
- `esp32_private_key.json` — RSA private key of ESP32
- `executor_pubkey.bin` — secp256k1 pubkey of executor
- `test_packet_engine.bin` — test packet
- `secrets.py` — Wi-Fi credentials (SSID, password)
- `programs/*.enc` — offline packets (physical delivery)


## Лицензия

Выпущено под **лицензией MIT**.

Основано на **стандарте TUR55** (Trust Unified Regulation), автор: NOMOS-H.
Оригинал спецификации: https://github.com/Tabintaban/Protocol_TUR55

---

## Ссылки

- **TUR55 Standard:** https://github.com/Tabintaban/Protocol_TUR55
- **MicroPython v1.24.1:** https://github.com/micropython/micropython/releases/tag/v1.24.1
- **ESP-IDF v5.2.2:** https://github.com/espressif/esp-idf/tree/v5.2.2
- **NIST SP 800-38D:** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
- **mbedTLS GCM:** https://mbed-tls.readthedocs.io/en/latest/kb/how-to/encrypt-with-aes-gcm/
- **ucryptography:** https://github.com/dmazzella/ucryptography
- **secp256k1-embedded-ecdh:** https://github.com/MicroPythonOS/secp256k1-embedded-ecdh
- **embit:** https://github.com/diybitcoinhardware/embit


