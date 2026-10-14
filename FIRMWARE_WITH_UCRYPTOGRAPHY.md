
# Прошивка с C-модулями (GCM + ucryptography + secp256k1)

**Дата:** 2026-10-14
**Статус:** ✅ Работает
**Цель:** кастомная прошивка MicroPython для TUR55/Bronze.

Полная инструкция сборки — в [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md).

---

## Что в прошивке

| Модуль | Что даёт | TUR55 | Статус |
|---|---|---|---|
| **gcm** (наш C-модуль) | AES-256-GCM | Раздел 4 | ✅ NIST 3/3 |
| **ucryptography** | RSA-OAEP | Раздел 4 | ✅ |
| **ucryptography** | BLAKE2s | Раздел 4 | ✅ |
| **ucryptography** | ECDSA (SECP256R1) | — | ✅ (не используется) |
| **usecp256k1** | ECDSA secp256k1 | Раздел 4 | ✅ **основной** |
| **ucryptography** | ~~Ed25519~~ | — | ❌ **отказ** (баг >96 байт) |

**Примечание:** Ed25519 **не используется**. Заменён на secp256k1 (см. `DECISIONS_LOG.md`, решение 7).

---

## Проверка на ESP32

### 1. GCM

```python
import gcm
key = bytes(32); iv = bytes(12); pt = b'hello'; aad = b''
ct, tag = gcm.encrypt(key, iv, pt, aad)
pt2 = gcm.decrypt(key, iv, ct, tag, aad)
print(pt2)  # b'hello'
```

**Ожидаемо:** `b'hello'`

### 2. BLAKE2s

```python
from cryptography.hazmat.primitives import hashes
h = hashes.Hash(hashes.BLAKE2s(32))
h.update(b'test')
print(h.finalize().hex())
```

**Ожидаемо:** hex-строка (64 символа).

### 3. RSA-OAEP

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
sk_rsa = rsa.generate_private_key(65537, 2048)
pk_rsa = sk_rsa.public_key()
mgf = padding.MGF1(hashes.SHA256())
oaep = padding.OAEP(mgf, hashes.SHA256(), None)
ct_rsa = pk_rsa.encrypt(b'secret', oaep)
pt_rsa = sk_rsa.decrypt(ct_rsa, oaep)
print(pt_rsa)  # b'secret'
```

**Ожидаемо:** `b'secret'`

### 4. ECDSA (SECP256R1) — вспомогательный

```python
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
sk_ec = ec.generate_private_key(ec.SECP256R1())
sig_ec = sk_ec.sign(b'test', ec.ECDSA(hashes.SHA256()))
sk_ec.public_key().verify(sig_ec, b'test', ec.ECDSA(hashes.SHA256()))
print('ECDSA SECP256R1 OK')
```

**Ожидаемо:** `ECDSA SECP256R1 OK`

### 5. secp256k1 — основной

```python
import usecp256k1
import hashlib

secret = hashlib.sha256(b"test").digest()
pubkey_obj = usecp256k1.ec_pubkey_create(secret)
pubkey = usecp256k1.ec_pubkey_serialize(pubkey_obj, usecp256k1.EC_COMPRESSED)

msg_hash = hashlib.sha256(b"hello").digest()
sig = usecp256k1.ecdsa_sign(msg_hash, secret)
der = usecp256k1.ecdsa_signature_serialize_der(sig)

sig_obj = usecp256k1.ecdsa_signature_parse_der(der)
pubkey_obj2 = usecp256k1.ec_pubkey_parse(pubkey)
ok = usecp256k1.ecdsa_verify(sig_obj, msg_hash, pubkey_obj2)
print('secp256k1 verify:', ok)
```

**Ожидаемо:** `secp256k1 verify: True`

### 6. Модули TUR55

```python
import tur55_packet
import program_loader
import execution_engine
import execution_sandbox
import gcm_adapter
import main
print('TUR55 modules: OK')
```

**Ожидаемо:** `TUR55 modules: OK`

### 7. Пайплайн TUR55 (финальная проверка)

**Перед запуском залить на ESP32:**
- `test_packet_engine.bin`
- `esp32_private_key.json`
- `executor_pubkey.bin`

**Запустить:**

```python
import test_engine_esp32
```

**Ожидаемо:**

```
========================================
engine test (ESP32)
========================================
1. ProgramLoader...          OK
2. Loading test_packet_engine.bin...  862 bytes
3. load_program...           command_id: 0xtest_engine_001
4. ExecutionEngine...        OK
5. execute_program...
setup done, x = 42
loop iter 0 x = 42
loop iter 1 x = 43
loop iter 2 x = 44
loop iter 3 x = 45
loop iter 4 x = 46
6. Results:
   setup success:    True
   loop iterations:  5
========================================
DONE
========================================
```

**Выйти:** `Ctrl+]`.

---

## Что НЕ используется

| Модуль | Почему |
|---|---|
| **Ed25519** | Баг на сообщениях >96 байт → заменён на secp256k1 |
| **ECDSA SECP256R1** | Работает, но TUR55 требует secp256k1 |
| **DES / 3DES** | Удалён в ESP-IDF v5.0 (заглушки `des3_stubs.c`) |

---

## Связанные документы

| Файл | Назначение |
|---|---|
| [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md) | Полная инструкция сборки |
| [TUR55_COMPLIANCE.md](TUR55_COMPLIANCE.md) | Таблица соответствия TUR55 |
| [ERRORS_AND_SOLUTIONS.md](ERRORS_AND_SOLUTIONS.md) | 28 ошибок и решений |
| [DECISIONS_LOG.md](DECISIONS_LOG.md) | 23 решения (Ed25519 → secp256k1) |
| [PROJECT_HISTORY.md](PROJECT_HISTORY.md) | История (Сессия 3 — ucryptography) |

---

## Ссылки

- **mbedTLS GCM:** https://mbed-tls.readthedocs.io/en/latest/kb/how-to/encrypt-with-aes-gcm/
- **ucryptography:** https://github.com/dmazzella/ucryptography
- **secp256k1-embedded-ecdh:** https://github.com/MicroPythonOS/secp256k1-embedded-ecdh
- **NIST SP 800-38D:** https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
- **TUR55 Standard:** https://github.com/Tabintaban/Protocol_TUR55
```

## Что изменилось

**Добавлено:**
- **Раздел «Что НЕ используется»** — Ed25519, SECP256R1, DES
- **Проверка модулей TUR55** (шаг 6)
- **Пайплайн TUR55** (шаг 7) — `test_engine_esp32`
- **Связанные документы** — ссылки на 5 файлов
- **Статус в таблице модулей** — что работает
- **Примечание** про Ed25519

**Изменено:**
- **Дата:** 11.10 → **14.10**
- **Заголовок:** «Прошивка с GCM + ucryptography» → **«Прошивка с C-модулями»**
- **Ed25519** — зачёркнут, помечен как **«отказ»**
- **usecp256k1** — помечен как **«основной»**
- **ECDSA SECP256R1** — помечен как **«вспомогательный»**

**Убрано:**
- Ed25519 из основного блока проверок (оставлен только в «Что НЕ используется»)

