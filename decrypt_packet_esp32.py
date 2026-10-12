"""
Расшифровка пакета TUR55 на ESP32.
"""

import tur55_packet
import json
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateNumbers, RSAPublicNumbers


def load_rsa_private_key(filename):
    """Восстанавливает RSA private key из JSON."""
    with open(filename, 'r') as f:
        components = json.load(f)

    n = int.from_bytes(bytes.fromhex(components['n']), 'big')
    e = components['e']
    d = int.from_bytes(bytes.fromhex(components['d']), 'big')
    p = int.from_bytes(bytes.fromhex(components['p']), 'big')
    q = int.from_bytes(bytes.fromhex(components['q']), 'big')
    dmp1 = int.from_bytes(bytes.fromhex(components['dmp1']), 'big')
    dmq1 = int.from_bytes(bytes.fromhex(components['dmq1']), 'big')
    iqmp = int.from_bytes(bytes.fromhex(components['iqmp']), 'big')

    pub_numbers = RSAPublicNumbers(e, n)
    priv_numbers = RSAPrivateNumbers(p, q, d, dmp1, dmq1, iqmp, pub_numbers)
    return priv_numbers.private_key()


def main():
    print("=" * 60)
    print("TUR55 Packet Decryption (ESP32)")
    print("=" * 60)

    # 1. Загрузка пакета
    print("\n1. Loading packet...")
    with open('test_packet.bin', 'rb') as f:
        packet = f.read()
    print("   Packet size:", len(packet))

    # 2. Загрузка ключей
    print("\n2. Loading keys...")
    esp32_private = load_rsa_private_key('esp32_private_key.json')
    print("   ESP32 RSA private key: OK")

    with open('executor_pubkey.bin', 'rb') as f:
        executor_pubkey = f.read()
    print("   Executor pubkey:", len(executor_pubkey), "bytes")

    # 3. Парсинг
    print("\n3. Parsing packet...")
    result = tur55_packet.parse_packet(packet, esp32_private, executor_pubkey)
    print("   Parsed OK")

    # 4. Показ
    print("\n4. Result:")
    print("   ", result)

    print("\n" + "=" * 60)
    print("✅ DECRYPTION SUCCESSFUL")
    print("=" * 60)


main()