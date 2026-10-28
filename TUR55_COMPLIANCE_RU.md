# TUR55_COMPLIANCE — таблица соответствия стандарту

**Проект:** ESP32_Python_FUEL
**Стандарт:** TUR55 (Trust Unified Regulation) — Open Standard
**Автор стандарта:** NOMOS-H
**Дата фиксации стандарта:** 2026-04-10
**Репозиторий стандарта:** https://github.com/Tabintaban/Protocol_TUR55
**Текущий статус:** **~95% TUR55/Bronze** (Bronze закрыт)
**Последнее обновление:** 2026-10-16

---

## О стандарте TUR55

**TUR55** — открытый стандарт для выполнения блокчейн-команд на IoT-устройствах (ESP32/MicroPython). Blockchain-agnostic, transport-independent, sandboxed execution.

### Четыре слоя архитектуры

| Слой | Назначение |
|---|---|
| **Event Layer** | Триггер из смарт-контракта |
| **Executor Layer** | Формирует зашифрованный пакет |
| **Delivery Layer** | Доставка (MQTT, HTTP, BLE, LoRaWAN, QR) |
| **Execution Layer** | Песочница, где скрипт безопасно исполняется |

**ESP32_Python_FUEL реализует `Execution Layer (Layer 4)`.**

---

## Криптография (раздел 4)

| Требование | Стандарт | Реализация | Статус |
|---|---|---|---|
| Симметричное шифрование | AES-256-GCM | `gcm` C-модуль на mbedTLS | ✅ **NIST 3/3 на ESP32** |
| Подпись | Ed25519 **или** secp256k1 | ECDSA secp256k1 (`usecp256k1`) | ✅ |
| Асимметричное шифрование | RSA-OAEP | `ucryptography` | ✅ |
| Хэш | BLAKE2s | `ucryptography` | ✅ |
| Хранение ключей | eFuse / Secure Element | `esp32_private_key.json` | ⏳ **Gold уровень** |

**Итог по разделу 4:** ✅ 4 из 5 для Bronze (eFuse — **требование Gold**, не Bronze)

---

## Формат пакета TUR55 (раздел 3.4)

**Реализация:** `tur55_packet.py`

### Структура

```
HEADER       8 байт (magic "TUR5", version, flags)
PUBKEY       length (1) + data (33 байта compressed secp256k1)
SESSION_KEY  length (2) + data (RSA-OAEP encrypted, ~256 байт)
SCRIPT       iv (12) + length (4) + data (AES-GCM) + tag (16)
SIGNATURE    length (2) + data (DER-encoded ECDSA secp256k1)
```

### Что покрывается подписью

**Подпись:** `HEADER + PUBKEY + SESSION_KEY + SCRIPT`
**AAD для GCM:** `HEADER + PUBKEY + SESSION_KEY`

### Соответствие

| Требование | Статус |
|---|---|
| HEADER с magic и version | ✅ |
| Публичный ключ экзекутора | ✅ |
| Сессионный ключ через RSA-OAEP | ✅ |
| Скрипт через AES-256-GCM | ✅ |
| Подпись ECDSA secp256k1 | ✅ |
| Tamper detection | ✅ |
| Round-trip CPython → ESP32 | ✅ |

**Итог по разделу 3.4:** ✅ полностью

---

## Конверт TUR55 (раздел 3.2)

**Реализация:** `program_loader.py` (валидация)

### Обязательные поля

| Поле | Тип | Статус |
|---|---|---|
| `tur55_version` | str | ✅ |
| `command_id` | str (непустая) | ✅ |
| `device_id` | str | ✅ |
| `source` | dict | ✅ |
| `execution` | dict | ✅ |
| `custom_data` | dict | ✅ |

### Поля `execution`

| Поле | Тип | Статус |
|---|---|---|
| `runtime_limit_ms` | int | ✅ |
| `memory_limit_kb` | int | ✅ |
| `permissions` | list | ✅ |
| `setup` | list (строк) | ✅ |
| `loop_logic` | list (строк) | ✅ |
| `functions` | list (строк) | ✅ |
| `expires` | int (опционально) | ✅ |
| `user_wallet` | str | ✅ (не валидируется) |
| `amount` | float | ✅ (не валидируется) |

**Итог по разделу 3.2:** ✅ полностью

---

## Replay protection (раздел 5)

**Реализация:** `program_loader.py`

| Требование | Реализация | Статус |
|---|---|---|
| Проверка `command_id` (replay) | `validate_command_id` — FIFO на 100 | ✅ |
| Сохранение между перезагрузками | NVS (`tur55_replay`) | ✅ |
| Fallback без NVS (CPython) | RAM | ✅ |
| Проверка `expires` | `validate_expires` — RTC, автоматически | ✅ |

**Логика проверок** (порядок):

1. `parse_packet` — подпись, GCM
2. `validate_program_structure` — конверт 3.2
3. `validate_permissions`
4. `validate_runtime_constraints`
5. `validate_expires` (опционально, только при `time_synced`)
6. `validate_command_id` (последним, чтобы не «сжечь» битым пакетом)

### Обновление раздела 5 (NTP и `expires`) — v3.5.0

С версии **v3.5.0** (26.10.2026) синхронизация времени выполняется **автоматически при каждом включении** ESP32:

1. **`boot.py`** — при загрузке подключается к Wi-Fi и синхронизирует время по NTP (по IP-адресам Google, Cloudflare, NIST). 3 попытки на каждый сервер. При неудаче — перезагрузка.
2. **`program_loader.py::validate_expires`** — использует **`machine.RTC().datetime()`** вместо `time.time()` (обход бага MicroPython 1.24.1, см. `DECISIONS_LOG.md` решение №33).
3. **Результат:** проверка `expires` работает **всегда** (а не только когда время было установлено вручную).

**Статус раздела 5:** ✅ **ЗАКРЫТО** (полностью автоматизировано).

**Итог по разделу 5:** ✅ **закрыто** (с оговоркой про `expires`)

**NVS:** `used_command_ids` сохраняются в NVS namespace `tur55_replay`. Проверено на ESP32 — replay переживает Ctrl+D. Fallback на RAM (CPython).

---

## Песочница (раздел 6)

**Реализация:** `execution_sandbox.py`, `memory_optimizer.py`

| Требование | Реализация | Статус |
|---|---|---|
| Whitelist модулей | `SafeImporter` | ✅ |
| Запрет опасных builtins | `eval`, `exec`, `compile`, `open`, `getattr` | ✅ |
| Таймаут | Кооперативный (`machine.Timer`) | ✅ |
| Лимит памяти | `_check_memory_usage` | ✅ |
| Лимиты из пакета | `limit_resources` | ✅ |
| Запрет относительных импортов | `level > 0` | ✅ |

### Whitelist модулей

**Разрешены:**
- `machine`, `time`, `math`, `struct`, `json`, `gc`

**Запрещены:**
- `sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`

**Итог по разделу 6:** ✅ полностью

**Оговорка:** таймаут **кооперативный** — не прерывает зависший C-код. Hard-guarantee отсутствует.

---

## Лог в UART (TUR55/Bronze, раздел 9)

**Реализация:** `main.py` (`Logger`) → `print()` → `stdout` → **UART0**

**TUR55 раздел 9** требует для **Bronze**: приём пакета, дешифровка, исполнение, **лог в UART**.

| Требование | Реализация | Статус |
|---|---|---|
| Лог в UART | `Logger` (5 уровней: DEBUG–CRITICAL) | ✅ |
| События запуска | `=== TUR55 Pipeline ===`, `Init ProgramLoader` | ✅ |
| События пакета | `Auto-found packet`, `command_id`, `device_id` | ✅ |
| События исполнения | `setup success`, `loop iterations`, `loop time_ms` | ✅ |
| События ошибок | `[ERROR] Validation failed`, `[WARNING]` | ✅ |
| События завершения | `=== Done ===` | ✅ |

**Как работает:**
- На ESP32: `print()` → **UART0** → USB-UART → COM-порт → miniterm
- На CPython: `print()` → **консоль** (для отладки)

**Проверено:** логи видны в `py -m serial.tools.miniterm COM3 115200`

**Итог:** ✅ **закрыто** (требование TUR55/Bronze выполнено)

---



## Delivery Layer (сетевой слой + физическая доставка)

**Реализация:** `mqtt_client.py`, `mqtt_publisher.py`, `main._find_packet()`

| Требование | Реализация | Статус |
|---|---|---|
| Приём по сети | `MQTTReceiver` (umqtt.simple) | ✅ |
| Отправка по сети | `MQTTPublisher` (paho-mqtt) | ✅ |
| Wi-Fi подключение | `network.WLAN` | ✅ |
| **Физическая доставка** | **`programs/program.enc`** | **✅** |
| **Автопоиск пакета** | **`main._find_packet()`** | **✅** |
| End-to-end (MQTT) | ESP32 принял 862 байта | ✅ |
| End-to-end (physical) | `Auto-found packet: programs/program.enc` | ✅ |

**Топик:** `tur55/device/esp32_001`
**Брокер:** `broker.emqx.io` (публичный) / локальный Mosquitto
**Папка:** `programs/program.enc` (офлайн, флешка / USB)

**Итог:** ✅ **закрыто** (тезис 8 TUR55 — Transport Freedom: MQTT + physical)

---


## Тезисы манифеста TUR55

| # | Тезис | Требование | Реализация |
|---|---|---|---|
| 5 | Sandbox | Изолированное выполнение | ✅ |
| 6 | Cryptographic Truth | AES-256-GCM + secp256k1 | ✅ |
| 7 | Blockchain Agnosticism | Не привязан к блокчейну | ✅ (не блокчейн-специфичен) |
| 8 | Transport Freedom | Transport-independent | ✅ (`load_program(bytes)` + MQTT + `programs/`) |
| 9 | Universal License Token | — | ❌ (не в Layer 4) |
| 11 | Secure Elements | eFuse / hardware key storage | ⏳ **Gold уровень** |

**Итог по тезисам:** ✅ 5 из 6 для Bronze (eFuse — **требование Gold**)

---

## Сводная таблица

| Раздел | Требование | Статус |
|---|---|---|
| **3.2** | Конверт TUR55 | ✅ |
| **3.4** | Формат пакета | ✅ |
| **4** | AES-256-GCM | ✅ NIST 3/3 |
| **4** | ECDSA secp256k1 | ✅ |
| **4** | RSA-OAEP | ✅ |
| **4** | BLAKE2s | ✅ |
| **4** | **eFuse** | ⏳ Gold (не Bronze) |
| **5** | `command_id` (replay) | ✅ |
| **5** | NVS (переживает перезагрузку) | ✅ |
| **5** | `expires` | ✅ (NTP) |
| **6** | Whitelist | ✅ |
| **6** | Таймаут | ✅ (кооперативный) |
| **6** | Лимит памяти | ✅ |
| **Delivery** | MQTT + physical | ✅ |
| **9** | **Лог в UART** | ✅ |

---

## Что закрыто

- ✅ **Раздел 3.2** — конверт TUR55
- ✅ **Раздел 3.4** — формат пакета (round-trip работает)
- ✅ **Раздел 4** — AES-256-GCM, ECDSA secp256k1, RSA-OAEP, BLAKE2s
- ✅ **Раздел 5** — replay protection + NVS
- ✅ **Раздел 6** — whitelist, таймаут, лимит памяти
- ✅ **Delivery Layer** — MQTT + physical (`programs/`) (тезис 8, Transport Freedom)
- ✅ **Лог в UART** — Logger (раздел 9, Bronze)

**TUR55/Bronze — закрыт полностью.**

## Что осталось (для Gold)

| # | Задача | Раздел TUR55 | Приоритет |
|---|---|---|---|
| 1 | **eFuse** для ключей | 4 | **Gold уровень** (не Bronze) |
| 2 | **Secure boot** | 9 | **Gold уровень** |
| 3 | **Документация** (README, BUILD_GCM) | — | низкий |

---

## Известные ограничения

1. **eFuse** — не реализован (**требование Gold**, не Bronze). Ключи в `esp32_private_key.json`.
2. **Кооперативный таймаут** — не прерывает зависший C-код. Hard-guarantee отсутствует.
3. **`used_command_ids` в NVS** — сохраняется между перезагрузками. ✅
4. **`expires` проверяется** — через NTP. ✅
5. **MQTT / сетевой стек** — реализованы. ✅
6. **Физическая доставка** — реализована (`programs/program.enc`). ✅
7. **Лог в UART** — реализован (Logger → stdout → UART0). ✅
8. **`os.dupterm`** — не используется (нет перехвата `print`).

---

## Ссылки

- **TUR55 Standard:** https://github.com/Tabintaban/Protocol_TUR55
- **ESP32_Python_FUEL:** https://github.com/Tabintaban/ESP32_Python_FUEL
- **NIST SP 800-38D:** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
- **MicroPython v1.24.1:** https://github.com/micropython/micropython/releases/tag/v1.24.1
- **ESP-IDF v5.2.2:** https://github.com/espressif/esp-idf/tree/v5.2.2

