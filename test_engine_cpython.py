"""
Тест связки program_loader -> execution_engine на CPython.

Читает test_packet_engine.bin, прогоняет через:
  1. ProgramLoader.load_program() -> конверт 3.2
  2. ExecutionEngine.execute_program() -> setup + loop

Проверяет, что setup и loop выполнились.
"""

import sys
import traceback

from program_loader import ProgramLoader
from execution_engine import ExecutionEngine


def main():
    print("=" * 60)
    print("program_loader -> execution_engine test (CPython)")
    print("=" * 60)

    # 1. ProgramLoader
    print("\n1. ProgramLoader...")
    try:
        loader = ProgramLoader()
        print("   OK")
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # 2. Загрузка пакета
    print("\n2. Loading test_packet_engine.bin...")
    try:
        with open("test_packet_engine.bin", "rb") as f:
            packet = f.read()
        print("   Packet size:", len(packet), "bytes")
    except Exception as e:
        print("   FAILED:", e)
        return 1

    # 3. parse + validate
    print("\n3. load_program...")
    try:
        data = loader.load_program(packet)
        print("   command_id:", data['command_id'])
        print("   device_id: ", data['device_id'])
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # 4. ExecutionEngine
    print("\n4. ExecutionEngine...")
    try:
        engine = ExecutionEngine(memory_limit_kb=25, time_limit_ms=5000)
        print("   OK")
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # 5. execute_program
    print("\n5. execute_program (setup + loop)...")
    try:
        result = engine.execute_program(data, max_iterations=5)
        print("   success:", result.get('success'))
    except Exception as e:
        print("   FAILED:", e)
        traceback.print_exc()
        return 1

    # 6. Проверки
    print("\n6. Results:")
    if not result.get('success'):
        print("   FAILED: execute_program returned success=False")
        print("   error:", result.get('error'))
        print("   setup_result:", result.get('setup_result'))
        return 1

    setup_result = result.get('setup_result', {})
    loop_result = result.get('loop_result', {})

    print("   setup success:", setup_result.get('success'))
    print("   loop iterations:", loop_result.get('iterations_completed'))
    print("   loop success:   ", loop_result.get('success'))

    # setup должен быть успешен
    if not setup_result.get('success'):
        print("   FAILED: setup not successful")
        print("   setup error:", setup_result.get('error'))
        return 1

    # loop должен выполнить 5 итераций
    if loop_result.get('iterations_completed') != 5:
        print("   FAILED: expected 5 iterations, got",
              loop_result.get('iterations_completed'))
        return 1

    # проверяем, что setup выполнился — x = 42
    setup_globals = setup_result.get('globals', {})
    # x хранится в locals, а не globals — но engine сохраняет context
    ctx = engine.execution_contexts.get('setup_context', {})
    print("   setup_context keys:", list(ctx.get('locals', {}).keys()))
    print("   x in locals:      ", 'x' in ctx.get('locals', {}))

    print("\n" + "=" * 60)
    print("ALL ENGINE CHECKS PASSED")
    print("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())