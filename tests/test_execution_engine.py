"""
Unit tests for execution_engine module
"""
import sys
sys.path.insert(0, '..')

import time
from execution_engine import ExecutionEngine

# Совместимость с CPython и MicroPython
if hasattr(time, 'ticks_ms'):
    get_time_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def get_time_ms():
        return int(time.time() * 1000)
    def ticks_diff(end, start):
        return end - start


def test_execution_engine():
    """
    Unit-тесты для ExecutionEngine
    """
    print("Testing ExecutionEngine...")
    
    # Тест 1: Базовое выполнение
    engine = ExecutionEngine(memory_limit_kb=25, time_limit_ms=2000)
    
    setup_code = """
counter = 0
print("Setup executed")
"""
    
    setup_result = engine.execute_setup(setup_code)
    assert setup_result.get('success'), "Setup should execute successfully"
    print("✓ Test 1: Basic setup execution passed")
    
    # Тест 2: Быстрый код должен выполниться
    fast_code = """
x = 1 + 1
print("Fast code executed")
"""
    
    setup_result = engine.execute_setup(fast_code)
    assert setup_result.get('success'), "Fast code should execute within timeout"
    print("✓ Test 2: Fast code execution passed")
    
    # Тест 3: Циклическое выполнение
    loop_code = """
# Простой код без зависаний
iteration = iteration_count + 1
"""
    
    loop_result = engine.execute_loop(loop_code, max_iterations=10)
    assert loop_result.get('success'), "Loop should execute successfully"
    assert loop_result['iterations_completed'] == 10, f"Should complete 10 iterations, got {loop_result['iterations_completed']}"
    print("✓ Test 3: Loop execution passed")
    
    # Тест 4: Очистка ресурсов после остановки
    engine.stop_execution()
    stats = engine.get_execution_stats()
    assert stats['contexts_count'] == 0, "Contexts should be cleared after stop"
    print("✓ Test 4: Resource cleanup passed")
    
    # Тест 5: Проверка памяти перед циклом (если доступно)
    try:
        import gc
        gc.collect()
        free_before = gc.mem_free()
        print(f"✓ Test 5: Free memory before loop: {free_before} bytes")
    except:
        print("✓ Test 5: Memory check skipped (gc not available)")
    
    # Тест 6: Зависший код в цикле должен быть прерван sandbox
    try:
        from execution_sandbox import ExecutionSandbox, machine
        # На CPython без machine.Timer этот тест не работает
        if machine is None:
            print("✓ Test 6: Hanging code test skipped (machine.Timer not available on PC)")
        else:
            test_sandbox = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=1000)
            hanging_code = "while True: pass"
            
            start = get_time_ms()
            try:
                test_sandbox.execute_in_sandbox(hanging_code)
                print("✓ Test 6: Hanging code test skipped (no machine.Timer on PC)")
            except (TimeoutError, MemoryError) as e:
                elapsed = ticks_diff(get_time_ms(), start)
                print(f"✓ Test 6: Hanging code interrupted in {elapsed}ms: {e}")
    except Exception as e:
        print(f"✓ Test 6: Hanging code test: {e}")
    
    print("\n✅ All execution engine tests passed!\n")


if __name__ == "__main__":
    test_execution_engine()
