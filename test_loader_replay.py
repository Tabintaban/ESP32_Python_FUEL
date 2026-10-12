"""
Тест replay protection и expires в ProgramLoader.

Проверяет:
  1. Первый load_program  -> OK
  2. Второй load_program  -> replay detected
  3. expires с синхронизацией -> expired
  4. set_time + свежий expires -> OK
"""

import sys
import traceback

from program_loader import ProgramLoader


def main():
    print("=" * 60)
    print("ProgramLoader: replay + expires test")
    print("=" * 60)

    # Читаем пакет
    with open("test_packet.bin", "rb") as f:
        packet_bytes = f.read()
    print("\nPacket size:", len(packet_bytes), "bytes")

    # ---- Тест 1: первый load ----
    print("\n--- Test 1: first load ---")
    loader = ProgramLoader()
    try:
        data = loader.load_program(packet_bytes)
        print("   OK, command_id:", data['command_id'])
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # ---- Тест 2: replay ----
    print("\n--- Test 2: replay (same packet again) ---")
    try:
        data = loader.load_program(packet_bytes)
        print("   FAILED: replay was NOT detected")
        return 1
    except ValueError as e:
        if "replay" in str(e).lower():
            print("   OK, replay detected:", e)
        else:
            print("   FAILED: wrong error:", e)
            return 1

    # ---- Тест 3: expires с синхронизацией (просрочен) ----
    print("\n--- Test 3: expires with time sync (expired) ---")
    loader2 = ProgramLoader()
    # expires в пакете = 1741500000 (~март 2025)
    # ставим current_time = 1800000000 (~2027)
    loader2.set_time(1800000000)
    print("   current_time:", loader2.current_time)
    print("   time_synced:", loader2.time_synced)
    try:
        data = loader2.load_program(packet_bytes)
        print("   FAILED: expired packet was accepted")
        return 1
    except ValueError as e:
        if "expired" in str(e).lower():
            print("   OK, expired detected:", e)
        else:
            print("   FAILED: wrong error:", e)
            return 1

    # ---- Тест 4: expires с синхронизацией (не просрочен) ----
    print("\n--- Test 4: expires with time sync (valid) ---")
    loader3 = ProgramLoader()
    # expires = 1741500000, ставим current_time = 1700000000 (~2023) -> ещё валиден
    loader3.set_time(1700000000)
    print("   current_time:", loader3.current_time)
    try:
        data = loader3.load_program(packet_bytes)
        print("   OK, packet accepted")
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("ALL REPLAY/EXPIRES CHECKS PASSED")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())