
# TUR55_COMPLIANCE — Standard Compliance Table

**Project:** ESP32_Python_FUEL
**Standard:** TUR55 (Trust Unified Regulation) — Open Standard
**Standard Author:** NOMOS-H
**Standard Fixation Date:** 2026-04-10
**Standard Repository:** https://github.com/Tabintaban/Protocol_TUR55
**Current Status:** **~95% TUR55/Bronze** (Bronze closed)
**Last Updated:** 2026-10-16

---

## About the TUR55 Standard

**TUR55** is an open standard for executing blockchain commands on IoT devices (ESP32/MicroPython). Blockchain-agnostic, transport-independent, sandboxed execution.

### Four Architecture Layers

| Layer | Purpose |
|---|---|
| **Event Layer** | Trigger from a smart contract |
| **Executor Layer** | Builds the encrypted packet |
| **Delivery Layer** | Delivery (MQTT, HTTP, BLE, LoRaWAN, QR) |
| **Execution Layer** | Sandbox where the script is safely executed |

**ESP32_Python_FUEL implements `Execution Layer (Layer 4)`.**

---

## Cryptography (Section 4)

| Requirement | Standard | Implementation | Status |
|---|---|---|---|
| Symmetric encryption | AES-256-GCM | `gcm` C-module on mbedTLS | ✅ **NIST 3/3 on ESP32** |
| Signature | Ed25519 **or** secp256k1 | ECDSA secp256k1 (`usecp256k1`) | ✅ |
| Asymmetric encryption | RSA-OAEP | `ucryptography` | ✅ |
| Hash | BLAKE2s | `ucryptography` | ✅ |
| Key storage | eFuse / Secure Element | `esp32_private_key.json` | ⏳ **Gold level** |

**Section 4 Result:** ✅ 4 out of 5 for Bronze (eFuse is a **Gold requirement**, not Bronze)

---

## TUR55 Packet Format (Section 3.4)

**Implementation:** `tur55_packet.py`

### Structure

```
HEADER       8 bytes (magic "TUR5", version, flags)
PUBKEY       length (1) + data (33 bytes compressed secp256k1)
SESSION_KEY  length (2) + data (RSA-OAEP encrypted, ~256 bytes)
SCRIPT       iv (12) + length (4) + data (AES-GCM) + tag (16)
SIGNATURE    length (2) + data (DER-encoded ECDSA secp256k1)
```

### What is covered by the signature

**Signature:** `HEADER + PUBKEY + SESSION_KEY + SCRIPT`
**AAD for GCM:** `HEADER + PUBKEY + SESSION_KEY`

### Compliance

| Requirement | Status |
|---|---|
| HEADER with magic and version | ✅ |
| Executor public key | ✅ |
| Session key via RSA-OAEP | ✅ |
| Script via AES-256-GCM | ✅ |
| ECDSA secp256k1 signature | ✅ |
| Tamper detection | ✅ |
| Round-trip CPython → ESP32 | ✅ |

**Section 3.4 Result:** ✅ fully compliant

---

## TUR55 Envelope (Section 3.2)

**Implementation:** `program_loader.py` (validation)

### Required Fields

| Field | Type | Status |
|---|---|---|
| `tur55_version` | str | ✅ |
| `command_id` | str (non-empty) | ✅ |
| `device_id` | str | ✅ |
| `source` | dict | ✅ |
| `execution` | dict | ✅ |
| `custom_data` | dict | ✅ |

### `execution` Fields

| Field | Type | Status |
|---|---|---|
| `runtime_limit_ms` | int | ✅ |
| `memory_limit_kb` | int | ✅ |
| `permissions` | list | ✅ |
| `setup` | list (of strings) | ✅ |
| `loop_logic` | list (of strings) | ✅ |
| `functions` | list (of strings) | ✅ |
| `expires` | int (optional) | ✅ |
| `user_wallet` | str | ✅ (not validated) |
| `amount` | float | ✅ (not validated) |

**Section 3.2 Result:** ✅ fully compliant

---

## Replay Protection (Section 5)

**Implementation:** `program_loader.py`

| Requirement | Implementation | Status |
|---|---|---|
| `command_id` check (replay) | `validate_command_id` — FIFO of 100 | ✅ |
| Persistence across reboots | NVS (`tur55_replay`) | ✅ |
| Fallback without NVS (CPython) | RAM | ✅ |
| `expires` check | `validate_expires` — RTC, automatic | ✅ |

**Validation Logic** (order):

1. `parse_packet` — signature, GCM
2. `validate_program_structure` — envelope 3.2
3. `validate_permissions`
4. `validate_runtime_constraints`
5. `validate_expires` (optional, only when `time_synced`)
6. `validate_command_id` (last, to avoid "burning" a `command_id` with a corrupted packet)

### Section 5 Update (NTP and `expires`) — v3.5.0

Since **v3.5.0** (2026-10-26), time synchronization is performed **automatically on every ESP32 boot**:

1. **`boot.py`** — on boot, connects to Wi-Fi and syncs time via NTP (using IP addresses of Google, Cloudflare, NIST). 3 attempts per server. Reboots on failure.
2. **`program_loader.py::validate_expires`** — uses **`machine.RTC().datetime()`** instead of `time.time()` (workaround for MicroPython 1.24.1 bug, see `DECISIONS_LOG.md` decision #33).
3. **Result:** `expires` validation works **always** (not only when time was set manually).

**Section 5 Status:** ✅ **CLOSED** (fully automated).

**Section 5 Result:** ✅ **closed** (with a note on `expires`)

**NVS:** `used_command_ids` are stored in the NVS namespace `tur55_replay`. Verified on ESP32 — replay protection survives Ctrl+D. Fallback to RAM (CPython).

---

## Sandbox (Section 6)

**Implementation:** `execution_sandbox.py`, `memory_optimizer.py`

| Requirement | Implementation | Status |
|---|---|---|
| Module whitelist | `SafeImporter` | ✅ |
| Blocking dangerous builtins | `eval`, `exec`, `compile`, `open`, `getattr` | ✅ |
| Timeout | Cooperative (`machine.Timer`) | ✅ |
| Memory limit | `_check_memory_usage` | ✅ |
| Limits from packet | `limit_resources` | ✅ |
| Blocking relative imports | `level > 0` | ✅ |

### Module Whitelist

**Allowed:**
- `machine`, `time`, `math`, `struct`, `json`, `gc`

**Blocked:**
- `sys`, `_thread`, `select`, `socket`, `ssl`, `network`, `uos`

**Section 6 Result:** ✅ fully compliant

**Note:** The timeout is **cooperative** — it does not interrupt a hanging C-code. Hard guarantee is absent.

---

## UART Logging (TUR55/Bronze, Section 9)

**Implementation:** `main.py` (`Logger`) → `print()` → `stdout` → **UART0**

**TUR55 Section 9** requires for **Bronze**: packet reception, decryption, execution, **UART logging**.

| Requirement | Implementation | Status |
|---|---|---|
| UART logging | `Logger` (5 levels: DEBUG–CRITICAL) | ✅ |
| Startup events | `=== TUR55 Pipeline ===`, `Init ProgramLoader` | ✅ |
| Packet events | `Auto-found packet`, `command_id`, `device_id` | ✅ |
| Execution events | `setup success`, `loop iterations`, `loop time_ms` | ✅ |
| Error events | `[ERROR] Validation failed`, `[WARNING]` | ✅ |
| Completion events | `=== Done ===` | ✅ |

**How it works:**
- On ESP32: `print()` → **UART0** → USB-UART → COM port → miniterm
- On CPython: `print()` → **console** (for debugging)

**Verified:** logs are visible in `py -m serial.tools.miniterm COM3 115200`

**Result:** ✅ **closed** (TUR55/Bronze requirement met)

---

## Delivery Layer (Network + Physical Delivery)

**Implementation:** `mqtt_client.py`, `mqtt_publisher.py`, `main._find_packet()`

| Requirement | Implementation | Status |
|---|---|---|
| Network reception | `MQTTReceiver` (umqtt.simple/robust) | ✅ |
| Network sending | `MQTTPublisher` (paho-mqtt) | ✅ |
| Wi-Fi connection | `network.WLAN` | ✅ |
| **Physical delivery** | **`programs/program.enc`** | **✅** |
| **Packet auto-discovery** | **`main._find_packet()`** | **✅** |
| End-to-end (MQTT) | ESP32 received 862 bytes | ✅ |
| End-to-end (physical) | `Auto-found packet: programs/program.enc` | ✅ |

**Topic:** `tur55/device/esp32_001`
**Broker:** `broker.emqx.io` (public) / local Mosquitto
**Folder:** `programs/program.enc` (offline, flash drive / USB)

**Result:** ✅ **closed** (TUR55 thesis 8 — Transport Freedom: MQTT + physical)

---

## TUR55 Manifest Theses

| # | Thesis | Requirement | Implementation |
|---|---|---|---|
| 5 | Sandbox | Isolated execution | ✅ |
| 6 | Cryptographic Truth | AES-256-GCM + secp256k1 | ✅ |
| 7 | Blockchain Agnosticism | Not tied to a specific blockchain | ✅ (blockchain-agnostic) |
| 8 | Transport Freedom | Transport-independent | ✅ (`load_program(bytes)` + MQTT + `programs/`) |
| 9 | Universal License Token | — | ❌ (not in Layer 4) |
| 11 | Secure Elements | eFuse / hardware key storage | ⏳ **Gold level** |

**Theses Result:** ✅ 5 out of 6 for Bronze (eFuse is a **Gold requirement**)

---

## Summary Table

| Section | Requirement | Status |
|---|---|---|
| **3.2** | TUR55 envelope | ✅ |
| **3.4** | Packet format | ✅ |
| **4** | AES-256-GCM | ✅ NIST 3/3 |
| **4** | ECDSA secp256k1 | ✅ |
| **4** | RSA-OAEP | ✅ |
| **4** | BLAKE2s | ✅ |
| **4** | **eFuse** | ⏳ Gold (not Bronze) |
| **5** | `command_id` (replay) | ✅ |
| **5** | NVS (persists across reboot) | ✅ |
| **5** | `expires` | ✅ (NTP) |
| **6** | Whitelist | ✅ |
| **6** | Timeout | ✅ (cooperative) |
| **6** | Memory limit | ✅ |
| **Delivery** | MQTT + physical | ✅ |
| **9** | **UART logging** | ✅ |

---

## What is closed

- ✅ **Section 3.2** — TUR55 envelope
- ✅ **Section 3.4** — packet format (round-trip works)
- ✅ **Section 4** — AES-256-GCM, ECDSA secp256k1, RSA-OAEP, BLAKE2s
- ✅ **Section 5** — replay protection + NVS
- ✅ **Section 6** — whitelist, timeout, memory limit
- ✅ **Delivery Layer** — MQTT + physical (`programs/`) (thesis 8, Transport Freedom)
- ✅ **UART logging** — Logger (section 9, Bronze)

**TUR55/Bronze — fully closed.**

## What remains (for Gold)

| # | Task | TUR55 Section | Priority |
|---|---|---|---|
| 1 | **eFuse** for keys | 4 | **Gold level** (not Bronze) |
| 2 | **Secure boot** | 9 | **Gold level** |
| 3 | **Documentation** (README, BUILD_GCM) | — | low |

---

### Testing Note: Resetting Replay Protection (NVS)

When testing with the same `command_id` (e.g., a transaction hash), ESP32 may reject the packet with `Command replay detected`. To manually clear the NVS history via `mpremote`, run:

```python
import esp32
nvs = esp32.NVS("tur55_replay")
try:
    nvs.erase_key("used_ids")
    nvs.commit()
    print("NVS cleared!")
except OSError:
    print("NVS is already empty.")
```

**Important:** This clears the entire command history. Use it only in a testing environment, never in production.


---

## Known Limitations

1. **eFuse** — not implemented (**Gold requirement**, not Bronze). Keys are in `esp32_private_key.json`.
2. **Cooperative timeout** — does not interrupt a hanging C-code. Hard guarantee is absent.
3. **`used_command_ids` in NVS** — persists across reboots. ✅
4. **`expires` is checked** — via NTP. ✅
5. **MQTT / network stack** — implemented. ✅
6. **Physical delivery** — implemented (`programs/program.enc`). ✅
7. **UART logging** — implemented (Logger → stdout → UART0). ✅
8. **`os.dupterm`** — not used (no `print` interception).

---

## Links

- **TUR55 Standard:** https://github.com/Tabintaban/Protocol_TUR55
- **ESP32_Python_FUEL:** https://github.com/Tabintaban/ESP32_Python_FUEL
- **NIST SP 800-38D:** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
- **MicroPython v1.24.1:** https://github.com/micropython/micropython/releases/tag/v1.24.1
- **ESP-IDF v5.2.2:** https://github.com/espressif/esp-idf/tree/v5.2.2
