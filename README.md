
# ESP32_Python_FUEL

**Secure Execution Layer (Layer 4) of the TUR55 protocol.**
Sandboxed MicroPython program execution for ESP32 with encryption, strict resource limits, and isolated runtime.

[![Status](https://img.shields.io/badge/TUR55--Bronze-75%25-yellow)]()
[![MicroPython](https://img.shields.io/badge/MicroPython-v1.24.1-blue)]()
[![ESP--IDF](https://img.shields.io/badge/ESP--IDF-v5.2.2-blue)]()

---

## What is TUR55?

**TUR55 (Trust Unified Regulation)** is an open standard for executing blockchain commands on IoT devices. It is blockchain-agnostic, transport-independent, and designed around sandboxed execution.

**Author:** NOMOS-H
**Fixed:** 2026-04-10
**Repository:** https://github.com/Tabintaban/Protocol_TUR55

### Four Sacred Layers

| Layer | Purpose |
|---|---|
| **Event Layer** | Trigger from a smart contract |
| **Executor Layer** | Forms the encrypted package |
| **Delivery Layer** | Transport (MQTT, HTTP, BLE, LoRaWAN, QR) |
| **Execution Layer** | Sandboxed execution on the device |

**ESP32_Python_FUEL implements `Layer 4 — Execution Layer`.**

---

## Status

**~75% TUR55/Bronze.**

| Section | Status |
|---|---|
| 3.2 — TUR55 envelope | ✅ |
| 3.4 — Packet format | ✅ works end-to-end |
| 4 — AES-256-GCM | ✅ NIST 3/3 on ESP32 |
| 4 — ECDSA secp256k1 | ✅ |
| 4 — RSA-OAEP | ✅ |
| 4 — BLAKE2s | ✅ |
| 4 — eFuse | ❌ |
| 5 — `command_id` (replay) | ✅ |
| 5 — `expires` | ⏳ optional |
| 6 — whitelist / timeout / memory | ✅ |

**Pipeline works end-to-end on CPython and ESP32.**

See [TUR55_COMPLIANCE.md](TUR55_COMPLIANCE.md) for the full compliance table.

---

## Architecture

### Pipeline

```
TUR55 packet (bytes)
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
validate expires           ── optional (if time_synced)
validate command_id        ── replay protection (FIFO 100)
    │
    ▼
execute_program()          ── execution_engine
    │
    ├─ setup (functions + setup lines)
    └─ loop (loop_logic lines)
    │
    ▼
sandbox                    ── execution_sandbox (whitelist + cooperative timeout)
```

### Modules

| Module | Purpose |
|---|---|
| `main.py` | Entry point — standard pipeline |
| `program_loader.py` | Parse + validate TUR55 envelope |
| `execution_engine.py` | Setup + loop execution |
| `execution_sandbox.py` | Sandbox (whitelist, timeout, memory) |
| `tur55_packet.py` | TUR55 packet format (build + parse) |
| `gcm_adapter.py` | Unified GCM interface |
| `gcm.py` | GCM on pure Python (CPython fallback) |
| `memory_optimizer.py` | Memory management |

---

## Cryptography

| Algorithm | Purpose | Implementation |
|---|---|---|
| **AES-256-GCM** | Symmetric encryption | C-module on mbedTLS |
| **ECDSA secp256k1** | Signature | `usecp256k1` (Bitcoin Core) |
| **RSA-OAEP** | Session key encryption | `ucryptography` |
| **BLAKE2s** | Hashing | `ucryptography` |

**Compliance:** AES-256-GCM passed **NIST SP 800-38D** tests (3/3) on ESP32.

**CPython compatibility:** `embit` (libsecp256k1-compatible) for signatures.

---

## Requirements

| Component | Version | Why |
|---|---|---|
| **MicroPython** | **v1.24.1** | Stable release |
| **ESP-IDF** | **v5.2.2** | Compatible with v1.24.1 |
| **ESP32** | ESP32-D0WDQ6-V3 (WROOM) | Without PSRAM |
| **Python (WSL)** | 3.10.12 | ESP-IDF requirement |

**ESP-IDF v5.1.2 and v5.3.2 — NOT suitable.**

---

## Quick Start

### 1. Build custom firmware

See [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md) for full instructions.

**Short version:**

```bash
# Activate ESP-IDF
. ~/esp/esp-idf-v5.2.2/export.sh

# Build MicroPython with C-modules
cd ~/micropython/ports/esp32
rm -rf build-ESP32_GENERIC
make BOARD=ESP32_GENERIC USER_C_MODULES=/home/tavintavan/cmodules/micropython.cmake
```

### 2. Flash ESP32

**Three files, three addresses:**

| File | Address |
|---|---|
| `bootloader.bin` | `0x1000` |
| `partition-table.bin` | `0x8000` |
| `micropython.bin` | `0x10000` |

```powershell
py -m esptool --chip esp32 --port COM3 --baud 460800 write-flash --flash-mode dio --flash-size 4MB --flash-freq 40m -z 0x1000 "bootloader.bin" 0x8000 "partition-table.bin" 0x10000 "micropython.bin"
```

**WARNING:** Do NOT flash `micropython.bin` at `0x1000` — this causes boot loop.

### 3. Upload modules to ESP32

Upload via MicroPico or `mpremote`:

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

### 4. Run

```python
import main
main.main()
```

**Expected output:**

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

## TUR55 Envelope Format (section 3.2)

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

## TUR55 Packet Format (section 3.4)

**Binary, JWE-inspired:**

```
HEADER       8 bytes  (magic "TUR5", version, flags)
PUBKEY       1 + 33   (compressed secp256k1)
SESSION_KEY  2 + ~256 (RSA-OAEP encrypted)
SCRIPT       12 + 4 + N + 16  (iv + length + ct + tag)
SIGNATURE    2 + M    (DER-encoded ECDSA secp256k1)
```

**Signature covers:** `HEADER + PUBKEY + SESSION_KEY + SCRIPT`
**AAD for GCM:** `HEADER + PUBKEY + SESSION_KEY`

### Build a packet (executor side)

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

## Security

| Measure | Implementation |
|---|---|
| Encryption | AES-256-GCM (NIST 3/3) |
| Signature | ECDSA secp256k1 |
| Key exchange | RSA-OAEP |
| Replay protection | `command_id` FIFO (100) |
| Sandbox | `SafeImporter` with whitelist |
| Blocked builtins | `eval`, `exec`, `compile`, `open`, `getattr` |
| Timeout | Cooperative (`machine.Timer`) |
| Memory limit | `_check_memory_usage` |
| Limits from packet | `limit_resources` |

### Allowed modules in sandbox

`machine`, `time`, `math`, `struct`, `json`, `gc`

### Blocked modules

`sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`

---

## Documentation

| File | Purpose |
|---|---|
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | Full history (9 sessions) |
| [DECISIONS_LOG.md](DECISIONS_LOG.md) | 23 key decisions |
| [ERRORS_AND_SOLUTIONS.md](ERRORS_AND_SOLUTIONS.md) | 28 errors and fixes |
| [TODO.md](TODO.md) | Current plan |
| [TUR55_COMPLIANCE.md](TUR55_COMPLIANCE.md) | Compliance table |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md) | Firmware build instructions |
| [FIRMWARE_WITH_UCRYPTOGRAPHY.md](FIRMWARE_WITH_UCRYPTOGRAPHY.md) | ucryptography details |

---

## Known Limitations

1. **eFuse** not implemented — keys stored in `esp32_private_key.json` (plaintext).
2. **Cooperative timeout** — does not interrupt hung C code. No hard guarantee.
3. **`used_command_ids` in RAM** — lost on reboot. Needs NVS.
4. **`expires` not checked** — no time source (NTP/MQTT not implemented).
5. **MQTT / network stack** — not implemented.
6. **Physical delivery** (`programs/program.enc`) — not implemented.
7. **`os.dupterm`** — not used (no `print` interception).

---

## Testing

| Test | Platform | Purpose |
|---|---|---|
| `test_program_loader.py` | CPython | ProgramLoader |
| `test_loader_replay.py` | CPython | Replay + expires |
| `test_engine_cpython.py` | CPython | Engine |
| `test_engine_esp32.py` | ESP32 | Engine (hardware) |
| `test_esp32.py` | ESP32 | ProgramLoader (hardware) |
| `test_tur55_packet.py` | CPython | Packet format |
| `test_tur55_packet_esp32.py` | ESP32 | Packet format (hardware) |
| `test_gcm.py` | CPython | GCM (pure Python) |
| `test_gcm_esp32.py` | ESP32 | GCM (C-module) |
| `test_hash.py` | CPython | Hashing |
| `test_rsa_esp32.py` | ESP32 | RSA-OAEP (hardware) |

---

## Project Structure


```
ESP32_Python_FUEL/
│
├── main.py                              # Entry point — standard pipeline
├── program_loader.py                    # Parse + validate TUR55 envelope
├── execution_engine.py                  # Setup + loop execution
├── execution_sandbox.py                 # Sandbox (whitelist, timeout, memory)
├── tur55_packet.py                      # TUR55 packet format (build + parse)
├── gcm_adapter.py                       # Unified GCM interface
├── gcm.py                               # Pure Python GCM (CPython fallback)
├── memory_optimizer.py                  # Memory management
│
├── build_packet_cpython.py              # Packet builder (executor side)
├── build_test_packet_cpython.py         # Test packet builder
│
├── test_program_loader.py               # ProgramLoader (CPython)
├── test_loader_replay.py                # Replay + expires
├── test_engine_cpython.py               # Engine (CPython)
├── test_engine_esp32.py                 # Engine (ESP32)
├── test_esp32.py                        # ProgramLoader (ESP32)
├── test_tur55_packet.py                 # Packet (CPython)
├── test_tur55_packet_esp32.py           # Packet (ESP32)
├── test_gcm.py                          # GCM (CPython)
├── test_gcm_esp32.py                    # GCM (ESP32)
├── test_hash.py                         # Hashing
├── test_rsa_esp32.py                    # RSA-OAEP (ESP32)
│
├── tests/                               # Unit tests (pytest-style)
│   ├── __init__.py
│   ├── test_execution_engine.py
│   ├── test_execution_sandbox.py
│   └── test_memory_optimizer.py
│
├── patches/                             # ucryptography patches
│   └── ucryptography/
│       ├── des3_stubs.c
│       ├── micropython.cmake
│       └── modcryptography.c
│
├── programs/                            # Encrypted program files (future)
│   └── readme.md
├── data/                                # Decrypted HTML/CSS/JS (future)
│   └── readme.md
├── utils/                               # Utilities
│   └── readme.md
├── .vscode/                             # VS Code settings
│   └── settings.json
│
├── PROJECT_HISTORY.md                   # 9 sessions
├── DECISIONS_LOG.md                     # 23 decisions
├── ERRORS_AND_SOLUTIONS.md              # 28 errors
├── TODO.md                              # Current plan
├── TUR55_COMPLIANCE.md                  # Compliance table
├── CHANGELOG.md                         # Version history
├── BUILD_GCM_FIRMWARE.md                # Firmware build
├── FIRMWARE_WITH_UCRYPTOGRAPHY.md       # ucryptography details
├── ESP32_MicroPython_Architecture_Plan.md
├── PROJECT_SUMMARY.md                   # (historical)
├── PROJECT_SUMMARY_RU.md                # (historical)
├── README.md                            # This file
├── README_RU.md                         # Russian version
├── LICENSE.md                           # MIT
└── .gitignore
```

**Runtime artifacts (gitignored):**
- `esp32_private_key.json` — RSA private key of ESP32
- `executor_pubkey.bin` — secp256k1 pubkey of executor
- `test_packet_engine.bin` — test packet

## License

Released under the **MIT License**.

Based on the **TUR55 Standard** (Trust Unified Regulation), author: NOMOS-H.
Original specification: https://github.com/Tabintaban/Protocol_TUR55

---

## References

- **TUR55 Standard:** https://github.com/Tabintaban/Protocol_TUR55
- **MicroPython v1.24.1:** https://github.com/micropython/micropython/releases/tag/v1.24.1
- **ESP-IDF v5.2.2:** https://github.com/espressif/esp-idf/tree/v5.2.2
- **NIST SP 800-38D:** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
- **mbedTLS GCM:** https://mbed-tls.readthedocs.io/en/latest/kb/how-to/encrypt-with-aes-gcm/
- **ucryptography:** https://github.com/dmazzella/ucryptography
- **secp256k1-embedded-ecdh:** https://github.com/MicroPythonOS/secp256k1-embedded-ecdh
- **embit:** https://github.com/diybitcoinhardware/embit

