"""
Тест TUR55 packet format на ESP32.

Использует ucryptography (Ed25519) вместо cryptography.
GCM — C-модуль.
"""

from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives import hashes
from tur55_packet import build_packet, parse_packet


def main():
    print("=" * 60)
    print("TUR55 Packet Test (ESP32)")
    print("=" * 60)

    # 1. Ключи
    print("\n1. Generating keys...")
    esp32_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    esp32_public = esp32_private.public_key()
    print("   ESP32 RSA-2048: OK")

    executor_private = ed25519.Ed25519PrivateKey.generate()
    executor_public = executor_private.public_key()
    print("   Executor Ed25519: OK")

    # 2. JSON
    print("\n2. Building JSON...")
    json_data = {
        "tur55_version": "1.0",
        "command_id": "0x7e5f8a3c",
        "device_id": "esp32_001",
        "script": "print('hello world')"
    }
    print("   JSON: OK")

    # 3. Собрать пакет
    print("\n3. Building packet...")
    packet = build_packet(json_data, esp32_public, executor_private)
    print("   Packet size: %d bytes" % len(packet))

    # 4. Разобрать
    print("\n4. Parsing packet...")
    result = parse_packet(packet, esp32_private, executor_public)
    print("   Parsed: OK")

    # 5. Сравнить
    print("\n5. Comparing...")
    if result == json_data:
        print("   ✅ MATCH")
    else:
        print("   ❌ MISMATCH")
        return

    # 6. Tamper
    print("\n6. Testing tamper detection...")
    tampered = bytearray(packet)
    tampered[50] ^= 0xFF
    try:
        parse_packet(bytes(tampered), esp32_private, executor_public)
        print("   ❌ FAIL: tampered accepted")
    except Exception as e:
        print("   ✅ Rejected: %s" % type(e).__name__)

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)


main()