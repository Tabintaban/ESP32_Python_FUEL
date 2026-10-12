"""
TUR55 Packet Format — JWE-inspired binary format.

ЭТОТ ФАЙЛ ИСПОЛЬЗУЕТСЯ В ДВУХ МЕСТАХ:

  1. ЭКЗЕКУТОР (сервер) — использует build_packet()
     Формирует зашифрованный пакет TUR55 из JSON-данных.

  2. ESP32 (устройство) — использует parse_packet()
     Разбирает и расшифровывает полученный пакет TUR55.

ПОДПИСЬ: ECDSA secp256k1 (соответствует TUR55 раздел 4).

Структура пакета:
  HEADER:      8 байт (magic "TUR5", version, flags)
  PUBKEY:      length (1) + data (33 байта compressed)
  SESSION_KEY: length (2) + data (RSA-OAEP encrypted)
  SCRIPT:      iv (12) + length (4) + data (AES-GCM) + tag (16)
  SIGNATURE:   length (2) + data (DER-encoded ECDSA sig)

Подпись покрывает: HEADER + PUBKEY + SESSION_KEY + SCRIPT
AAD для GCM:       HEADER + PUBKEY + SESSION_KEY
"""

import struct
import json
import os
import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Попытка использовать разные API для CPython / ESP32
try:
    # ESP32
    import usecp256k1
    _HAS_UECP = True
except ImportError:
    # CPython
    from cryptography.hazmat.primitives.asymmetric import ec
    _HAS_UECP = False

# CPython: embit для secp256k1 (совместим с usecp256k1)
try:
    from embit import ec as embit_ec
    _HAS_EMBIT = True
except ImportError:
    _HAS_EMBIT = False

# CPython: embit для secp256k1 (совместим с usecp256k1)
try:
    from embit import ec as embit_ec
    _HAS_EMBIT = True
except ImportError:
    _HAS_EMBIT = False

import gcm_adapter as gcm


MAGIC = b'TUR5'
VERSION = 0x0001


# ====================================================================
# ECDSA secp256k1 — обёртка для CPython и ESP32
# ====================================================================

def _ecdsa_keygen():
    """
    Генерирует пару ключей secp256k1.

    Returns:
        (secret_bytes, public_bytes) — 32 байта secret, 33 байта compressed pubkey
    """
    if _HAS_UECP:
        # ESP32: генерируем secret через os.urandom
        secret = os.urandom(32)
        while not usecp256k1.ec_seckey_verify(secret):
            secret = os.urandom(32)
        pubkey_obj = usecp256k1.ec_pubkey_create(secret)
        pubkey_bytes = usecp256k1.ec_pubkey_serialize(pubkey_obj, usecp256k1.EC_COMPRESSED)
        return secret, pubkey_bytes
    else:
        # CPython: используем cryptography
        sk = ec.generate_private_key(ec.SECP256K1())
        secret = sk.private_numbers().private_value.to_bytes(32, 'big')
        pub_numbers = sk.public_key().public_numbers()
        x = pub_numbers.x.to_bytes(32, 'big')
        y = pub_numbers.y.to_bytes(32, 'big')
        # Compressed: 0x02/0x03 + x
        prefix = 0x02 if (y[-1] & 1) == 0 else 0x03
        pubkey_bytes = bytes([prefix]) + x
        return secret, pubkey_bytes

def _ecdsa_sign(msg_hash, secret):
    """
    Подписывает 32-байтный хеш.

    Returns:
        bytes — DER-encoded signature
    """
    if _HAS_UECP:
        sig_obj = usecp256k1.ecdsa_sign(msg_hash, secret)
        return usecp256k1.ecdsa_signature_serialize_der(sig_obj)
    elif _HAS_EMBIT:
        from embit.ec import PrivateKey
        priv = PrivateKey(secret)
        sig = priv.sign(msg_hash)
        return sig.serialize()
    else:
        raise NotImplementedError("No ECDSA signer available")
    
def _ecdsa_verify(sig_der, msg_hash, pubkey_bytes):
    """
    Проверяет подпись.

    Returns:
        bool
    """
    if _HAS_UECP:
        sig_obj = usecp256k1.ecdsa_signature_parse_der(sig_der)
        pubkey_obj = usecp256k1.ec_pubkey_parse(pubkey_bytes)
        return usecp256k1.ecdsa_verify(sig_obj, msg_hash, pubkey_obj)
    elif _HAS_EMBIT:
        from embit.ec import PublicKey, Signature
        pub = PublicKey.parse(pubkey_bytes)
        sig = Signature.parse(sig_der)
        return pub.verify(sig, msg_hash)
    else:
        raise NotImplementedError("No ECDSA verifier available")

# ====================================================================
# ДЛЯ ЭКЗЕКУТОРА (сервер)
# ====================================================================

def build_packet(json_data, esp32_public_key, executor_secret):
    """
    Формирует пакет TUR55.

    Используется НА ЭКЗЕКУТОРЕ (сервере).

    Args:
        json_data: dict с полями
        esp32_public_key: публичный RSA-ключ ESP32
        executor_secret: приватный ключ secp256k1 экзекутора (32 байта)

    Returns:
        bytes — пакет TUR55
    """
    # 1. Публичный ключ экзекутора
    if _HAS_UECP:
        pubkey_obj = usecp256k1.ec_pubkey_create(executor_secret)
        executor_pubkey = usecp256k1.ec_pubkey_serialize(pubkey_obj, usecp256k1.EC_COMPRESSED)
    else:
        raise NotImplementedError("CPython build — реализуем позже")

    # 2. JSON
    plaintext = json.dumps(json_data).encode('utf-8')

    # 3. Сессионный ключ (32 байта)
    session_key = os.urandom(32)

    # 4. HEADER
    header = MAGIC + struct.pack('>HH', VERSION, 0x0000)

    # 5. PUBKEY part
    pubkey_part = bytes([len(executor_pubkey)]) + executor_pubkey

    # 6. Шифруем сессионный ключ RSA-OAEP
    mgf = padding.MGF1(hashes.SHA256())
    oaep = padding.OAEP(mgf, hashes.SHA256(), None)
    enc_session_key = esp32_public_key.encrypt(session_key, oaep)

    session_key_part = struct.pack('>H', len(enc_session_key)) + enc_session_key

    # 7. AAD = HEADER + PUBKEY + SESSION_KEY
    aad = header + pubkey_part + session_key_part

    # 8. Шифруем скрипт
    iv = os.urandom(12)
    ct, tag = gcm.encrypt(session_key, iv, plaintext, aad)

    script_part = iv + struct.pack('>I', len(ct)) + ct + tag

    # 9. Подпись ECDSA
    data_to_sign = header + pubkey_part + session_key_part + script_part
    msg_hash = hashlib.sha256(data_to_sign).digest()
    signature = _ecdsa_sign(msg_hash, executor_secret)

    # 10. SIGNATURE part
    signature_part = struct.pack('>H', len(signature)) + signature

    # 11. Собираем
    return header + pubkey_part + session_key_part + script_part + signature_part


# ====================================================================
# ДЛЯ ESP32 (устройство)
# ====================================================================

def parse_packet(packet, esp32_private_key, executor_pubkey_expected=None):
    """
    Разбирает и расшифровывает пакет TUR55.

    Используется НА ESP32.

    Args:
        packet: bytes — пакет TUR55
        esp32_private_key: приватный RSA-ключ ESP32
        executor_pubkey_expected: (опционально) ожидаемый pubkey экзекутора

    Returns:
        dict — расшифрованный JSON
    """
    offset = 0

    # 1. HEADER
    magic = packet[offset:offset+4]
    if magic != MAGIC:
        raise ValueError("Invalid magic")
    offset += 4
    version, flags = struct.unpack('>HH', packet[offset:offset+4])
    if version != VERSION:
        raise ValueError("Unsupported version")
    offset += 4
    header = packet[0:8]

    # 2. PUBKEY
    pk_len = packet[offset]
    offset += 1
    executor_pubkey = packet[offset:offset+pk_len]
    offset += pk_len
    pubkey_part = packet[8:offset]

    # 3. SESSION_KEY
    sk_len = struct.unpack('>H', packet[offset:offset+2])[0]
    offset += 2
    enc_session_key = packet[offset:offset+sk_len]
    offset += sk_len
    session_key_part = packet[8+len(pubkey_part):offset]

    # 4. SCRIPT
    iv = packet[offset:offset+12]
    offset += 12
    ct_len = struct.unpack('>I', packet[offset:offset+4])[0]
    offset += 4
    ct = packet[offset:offset+ct_len]
    offset += ct_len
    tag = packet[offset:offset+16]
    offset += 16
    script_part = packet[8+len(pubkey_part)+len(session_key_part):offset]

    # 5. SIGNATURE
    sig_len = struct.unpack('>H', packet[offset:offset+2])[0]
    offset += 2
    signature = packet[offset:offset+sig_len]
    offset += sig_len

    # 6. Проверяем подпись
    data_to_verify = header + pubkey_part + session_key_part + script_part
    msg_hash = hashlib.sha256(data_to_verify).digest()
    if not _ecdsa_verify(signature, msg_hash, executor_pubkey):
        raise ValueError("Invalid signature")

    # 7. Расшифровка сессионного ключа
    mgf = padding.MGF1(hashes.SHA256())
    oaep = padding.OAEP(mgf, hashes.SHA256(), None)
    session_key = esp32_private_key.decrypt(enc_session_key, oaep)

    # 8. AAD
    aad = header + pubkey_part + session_key_part

    # 9. Расшифровка скрипта
    plaintext = gcm.decrypt(session_key, iv, ct, tag, aad)

    # 10. JSON
    return json.loads(plaintext.decode('utf-8'))