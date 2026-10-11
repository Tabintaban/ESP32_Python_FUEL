# Прошивка с GCM + ucryptography

**Дата:** 2026-10-11  
**Статус:** ✅ Работает

## Что в прошивке

| Модуль | Что даёт | TUR55 |
|---|---|---|
| **gcm** (наш C-модуль) | AES-256-GCM | Раздел 4 |
| **ucryptography** | Ed25519 | Раздел 4 |
| **ucryptography** | BLAKE2s | Раздел 4 |
| **ucryptography** | RSA-OAEP | Раздел 4 |
| **ucryptography** | ECDSA | Раздел 4 |

## Проверка на ESP32

```python
# GCM
import gcm
key = bytes(32); iv = bytes(12); pt = b'hello'; aad = b''
ct, tag = gcm.encrypt(key, iv, pt, aad)
pt2 = gcm.decrypt(key, iv, ct, tag, aad)
print(pt2)  # b'hello'

# Ed25519
from cryptography.hazmat.primitives.asymmetric import ed25519
sk = ed25519.Ed25519PrivateKey.generate()
pk = sk.public_key()
sig = sk.sign(b'test')
pk.verify(sig, b'test')
print('Ed25519 OK')

# BLAKE2s
from cryptography.hazmat.primitives import hashes
h = hashes.Hash(hashes.BLAKE2s(32))
h.update(b'test')
print(h.finalize().hex())

# RSA-OAEP
from cryptography.hazmat.primitives.asymmetric import rsa, padding
sk_rsa = rsa.generate_private_key(65537, 2048)
pk_rsa = sk_rsa.public_key()
mgf = padding.MGF1(hashes.SHA256())
oaep = padding.OAEP(mgf, hashes.SHA256(), None)
ct_rsa = pk_rsa.encrypt(b'secret', oaep)
pt_rsa = sk_rsa.decrypt(ct_rsa, oaep)
print(pt_rsa)  # b'secret'

# ECDSA
from cryptography.hazmat.primitives.asymmetric import ec
sk_ec = ec.generate_private_key(ec.SECP256R1())
sig_ec = sk_ec.sign(b'test', ec.ECDSA(hashes.SHA256()))
sk_ec.public_key().verify(sig_ec, b'test', ec.ECDSA(hashes.SHA256()))
print('ECDSA OK')