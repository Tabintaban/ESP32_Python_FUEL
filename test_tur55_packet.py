"""
Тест TUR55 packet format на CPython.

Проверяет build_packet + parse_packet (round-trip).
"""

from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from tur55_packet import build_packet, parse_packet


def main():
    print("=" * 60)
    print("TUR55 Packet Test (CPython)")
    print("=" * 60)

    # 1. Генерируем ключи
    print("\n1. Generating keys...")
    esp32_private = rsa.generate_private_key(65537, 2048)
    esp32_public = esp32_private.public_key()
    print("   ESP32 RSA-2048: OK")

    executor_private = ed25519.Ed25519PrivateKey.generate()
    executor_public = executor_private.public_key()
    print("   Executor Ed25519: OK")

    # 2. Формируем JSON
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
            "expires": 1741500000
        },
        "custom_data": {
            "action": "unlock",
            "duration": 30
        },
        "script": "print('hello world')"
    }
    print("   JSON: OK")

    # 3. Собираем пакет
    print("\n3. Building packet...")
    packet = build_packet(json_data, esp32_public, executor_private)
    print("   Packet size: %d bytes" % len(packet))

    # 4. Разбираем пакет
    print("\n4. Parsing packet...")
    result = parse_packet(packet, esp32_private, executor_public)
    print("   Parsed: OK")

    # 5. Сравниваем
    print("\n5. Comparing...")
    if result == json_data:
        print("   ✅ MATCH: parsed == original")
    else:
        print("   ❌ MISMATCH")
        print("   Original:", json_data)
        print("   Parsed:  ", result)
        return False

    # 6. Проверка целостности (tamper)
    print("\n6. Testing tamper detection...")
    tampered = bytearray(packet)
    tampered[50] ^= 0xFF  # меняем байт в середине
    try:
        parse_packet(bytes(tampered), esp32_private, executor_public)
        print("   ❌ FAIL: tampered packet accepted!")
        return False
    except Exception as e:
        print("   ✅ Tampered packet rejected: %s" % type(e).__name__)

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    return True


if __name__ == '__main__':
    main()