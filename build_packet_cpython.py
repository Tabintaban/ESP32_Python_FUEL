"""
TUR55 Packet Builder для CPython.

Использует cryptography (cryptography.hazmat) для ECDSA secp256k1
и RSA-OAEP. Результат совместим с parse_packet на ESP32.
"""

import struct
import json
import os
import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from embit import ec as embit_ec
from embit import hashes as embit_hashes


MAGIC = b'TUR5'
VERSION = 0x0001


def aes_gcm_encrypt(key, iv, plaintext, aad):
    """AES-256-GCM через cryptography."""
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    encryptor = cipher.encryptor()
    if aad:
        encryptor.authenticate_additional_data(aad)
    ct = encryptor.update(plaintext) + encryptor.finalize()
    tag = encryptor.tag
    return ct, tag


def ecdsa_keygen():
    """Генерирует пару ключей secp256k1 через embit."""
    import os as _os
    secret = _os.urandom(32)
    sk = embit_ec.PrivateKey(secret)
    pubkey = sk.get_public_key().serialize()
    return sk, secret, pubkey


def ecdsa_sign(sk, msg_hash):
    """Подписывает хеш через embit (libsecp256k1-совместимо)."""
    sig = sk.sign(msg_hash)
    return sig.serialize()


def build_packet(json_data, esp32_public_key, executor_sk, executor_pubkey):
    """
    Формирует пакет TUR55.

    Args:
        json_data: dict
        esp32_public_key: RSA public key ESP32
        executor_sk: ECDSA private key (cryptography object)
        executor_pubkey: bytes, 33 байта compressed secp256k1

    Returns:
        bytes — пакет
    """
    # 1. JSON
    plaintext = json.dumps(json_data).encode('utf-8')

    # 2. Сессионный ключ
    session_key = os.urandom(32)

    # 3. HEADER
    header = MAGIC + struct.pack('>HH', VERSION, 0x0000)

    # 4. PUBKEY
    pubkey_part = bytes([len(executor_pubkey)]) + executor_pubkey

    # 5. RSA-OAEP encrypt session_key
    mgf = padding.MGF1(hashes.SHA256())
    oaep = padding.OAEP(mgf, hashes.SHA256(), None)
    enc_session_key = esp32_public_key.encrypt(session_key, oaep)
    session_key_part = struct.pack('>H', len(enc_session_key)) + enc_session_key

    # 6. AAD
    aad = header + pubkey_part + session_key_part

    # 7. AES-GCM
    iv = os.urandom(12)
    ct, tag = aes_gcm_encrypt(session_key, iv, plaintext, aad)
    script_part = iv + struct.pack('>I', len(ct)) + ct + tag

    # 8. ECDSA подпись
    data_to_sign = header + pubkey_part + session_key_part + script_part
    msg_hash = hashlib.sha256(data_to_sign).digest()
    signature = ecdsa_sign(executor_sk, msg_hash)

    # 9. SIGNATURE part
    signature_part = struct.pack('>H', len(signature)) + signature

    # 10. Собираем
    return header + pubkey_part + session_key_part + script_part + signature_part


def main():
    print("=" * 60)
    print("TUR55 Packet Builder (CPython)")
    print("=" * 60)

    # 1. Генерируем ключи
    print("\n1. Generating keys...")

    # ESP32 RSA-2048 (для теста — генерируем здесь)
    esp32_private = rsa.generate_private_key(65537, 2048)
    esp32_public = esp32_private.public_key()
    print("   ESP32 RSA-2048: OK")

    # Экзекутор secp256k1
    exec_sk, exec_secret, exec_pubkey = ecdsa_keygen()
    print("   Executor secp256k1: OK")
    print("   Pubkey:", exec_pubkey.hex())

    # 2. JSON (конверт TUR55, раздел 3.2)
    print("\n2. Building JSON...")
    json_data = {
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
            "setup": ["led = machine.Pin(2, machine.Pin.OUT)"],
            "loop_logic": ["led.value(1)", "time.sleep(0.5)"],
            "functions": []
        },
        "custom_data": {
            "action": "unlock",
            "duration": 30
        }
    }
    print("   JSON:", json_data)

    # 3. Пакет
    print("\n3. Building packet...")
    packet = build_packet(json_data, esp32_public, exec_sk, exec_pubkey)
    print("   Packet size:", len(packet), "bytes")

    # 4. Сохраняем пакет
    print("\n4. Saving packet...")
    with open("test_packet.bin", "wb") as f:
        f.write(packet)
    print("   Saved: test_packet.bin")

    # 5. Сохраняем ключи для ESP32
    print("\n5. Saving keys for ESP32...")

    # RSA private key — все компоненты
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
    print("   Saved: esp32_private_key.json")

    # Публичный ключ экзекутора
    with open("executor_pubkey.bin", "wb") as f:
        f.write(exec_pubkey)
    print("   Saved: executor_pubkey.bin")

    print("\n" + "=" * 60)
    print("Packet ready for ESP32")
    print("=" * 60)


if __name__ == '__main__':
    main()
