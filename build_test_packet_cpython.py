"""
Генерация тестового пакета TUR55 для проверки связки
program_loader -> execution_engine на CPython.

Код в пакете — безопасный, работает без machine:
    setup:      x = 42
    loop_logic: print('loop', x); x = x + 1
"""

import struct
import json
import os
import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from embit import ec as embit_ec


MAGIC = b'TUR5'
VERSION = 0x0001


def aes_gcm_encrypt(key, iv, plaintext, aad):
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()
    if aad:
        encryptor.authenticate_additional_data(aad)
    ct = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag
    return ct, tag


def ecdsa_sign(sk, msg_hash):
    sig = sk.sign(msg_hash)
    return sig.serialize()


def build_packet(json_data, esp32_public_key, executor_sk, executor_pubkey):
    plaintext = json.dumps(json_data).encode('utf-8')
    session_key = os.urandom(32)
    header = MAGIC + struct.pack('>HH', VERSION, 0x0000)
    pubkey_part = bytes([len(executor_pubkey)]) + executor_pubkey

    mgf = padding.MGF1(hashes.SHA256())
    oaep = padding.OAEP(mgf, hashes.SHA256(), None)
    enc_session_key = esp32_public_key.encrypt(session_key, oaep)
    session_key_part = struct.pack('>H', len(enc_session_key)) + enc_session_key

    aad = header + pubkey_part + session_key_part

    iv = os.urandom(12)
    ct, tag = aes_gcm_encrypt(session_key, iv, plaintext, aad)
    script_part = iv + struct.pack('>I', len(ct)) + ct + tag

    data_to_sign = header + pubkey_part + session_key_part + script_part
    msg_hash = hashlib.sha256(data_to_sign).digest()
    signature = ecdsa_sign(executor_sk, msg_hash)
    signature_part = struct.pack('>H', len(signature)) + signature

    return header + pubkey_part + session_key_part + script_part + signature_part


def main():
    print("=" * 60)
    print("TUR55 test packet builder (for engine test)")
    print("=" * 60)

    # 1. Ключи
    esp32_private = rsa.generate_private_key(65537, 2048)
    esp32_public = esp32_private.public_key()

    exec_secret = os.urandom(32)
    exec_sk = embit_ec.PrivateKey(exec_secret)
    exec_pubkey = exec_sk.get_public_key().sec()

    print("ESP32 RSA-2048: OK")
    print("Executor secp256k1:", exec_pubkey.hex())

    # 2. Конверт 3.2 — безопасный код для CPython
    json_data = {
        "tur55_version": "1.0",
        "command_id": "0xtest_engine_001",
        "device_id": "cpython_test",
        "source": {
            "smart_contract": "0x0",
            "transaction_hash": "0x0",
            "block_number": 0
        },
        "execution": {
            "runtime_limit_ms": 5000,
            "memory_limit_kb": 25,
            "permissions": ["time", "math"],
            "functions": [],
            "setup": [
                "x = 42",
                "print('setup done, x =', x)"
            ],
            "loop_logic": [
                "print('loop iter', iteration_count, 'x =', x)",
                "x = x + 1"
            ]
        },
        "custom_data": {
            "purpose": "engine test"
        }
    }
    print("JSON envelope: OK")

    # 3. Пакет
    packet = build_packet(json_data, esp32_public, exec_sk, exec_pubkey)
    print("Packet size:", len(packet), "bytes")

    # 4. Сохраняем
    with open("test_packet_engine.bin", "wb") as f:
        f.write(packet)
    print("Saved: test_packet_engine.bin")

    # 5. Ключи для ESP32-формата
    priv_numbers = esp32_private.private_numbers()
    pub_numbers = priv_numbers.public_numbers

    components = {
        "n": pub_numbers.n.to_bytes(256, 'big').hex(),
        "e": pub_numbers.e,
        "d": priv_numbers.d.to_bytes(256, 'big').hex(),
        "p": priv_numbers.p.to_bytes(128, 'big').hex(),
        "q": priv_numbers.q.to_bytes(128, 'big').hex(),
        "dmp1": priv_numbers.dmp1.to_bytes(128, 'big').hex(),
        "dmq1": priv_numbers.dmq1.to_bytes(128, 'big').hex(),
        "iqmp": priv_numbers.iqmp.to_bytes(128, 'big').hex(),
    }

    with open("esp32_private_key.json", "w") as f:
        json.dump(components, f)
    print("Saved: esp32_private_key.json")

    with open("executor_pubkey.bin", "wb") as f:
        f.write(exec_pubkey)
    print("Saved: executor_pubkey.bin")

    print("=" * 60)


if __name__ == '__main__':
    main()