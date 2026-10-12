"""
Тест ProgramLoader на CPython.

Читает test_packet.bin, прогоняет через ProgramLoader.load_program(),
проверяет результат.
"""

import sys
import traceback

from program_loader import ProgramLoader


def main():
    print("=" * 60)
    print("ProgramLoader test (CPython)")
    print("=" * 60)

    # 1. Инициализация
    print("\n1. Initializing ProgramLoader...")
    try:
        loader = ProgramLoader()
        print("   OK")
        print("   executor_pubkey:", loader.executor_pubkey.hex())
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # 2. Загрузка пакета
    print("\n2. Loading test_packet.bin...")
    try:
        with open("test_packet.bin", "rb") as f:
            packet_bytes = f.read()
        print("   Packet size:", len(packet_bytes), "bytes")
    except Exception as e:
        print("   FAILED:", e)
        return 1

    # 3. Разбор
    print("\n3. Parsing packet...")
    try:
        data = loader.load_program(packet_bytes)
        print("   OK")
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # 4. Проверка полей конверта 3.2
    print("\n4. Checking envelope fields...")
    checks = [
        ('tur55_version', 'str'),
        ('command_id', 'str'),
        ('device_id', 'str'),
        ('source', 'dict'),
        ('execution', 'dict'),
        ('custom_data', 'dict'),
    ]
    for field, expected_type in checks:
        value = data.get(field)
        ok = value is not None
        print("   %-15s %s" % (field, 'OK' if ok else 'MISSING'))
        if not ok:
            return 1

    # 5. Значения
    print("\n5. Values:")
    print("   tur55_version:", data['tur55_version'])
    print("   command_id:   ", data['command_id'])
    print("   device_id:    ", data['device_id'])
    print("   source:       ", data['source'])
    print("   custom_data:  ", data['custom_data'])
    print("   execution.permissions:", data['execution'].get('permissions'))
    print("   execution.setup:      ", data['execution'].get('setup'))
    print("   execution.loop_logic: ", data['execution'].get('loop_logic'))

    # 6. Кэш
    print("\n6. Cache check...")
    cached = loader.get_cached_program(data['command_id'])
    print("   Cached:", 'OK' if cached else 'MISSING')

    print("\n" + "=" * 60)
    print("ALL CHECKS PASSED")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())