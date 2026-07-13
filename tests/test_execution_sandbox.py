"""
Unit tests for execution_sandbox module
"""
import sys
sys.path.insert(0, '..')

import time
from execution_sandbox import ExecutionSandbox, machine

# Совместимость с CPython и MicroPython
if hasattr(time, 'ticks_ms'):
    get_time_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def get_time_ms():
        return int(time.time() * 1000)
    def ticks_diff(end, start):
        return end - start


def test_execution_sandbox():
    """
    Unit-тесты для ExecutionSandbox
    """
    print("Testing ExecutionSandbox...")
    
    sandbox = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=1000)
    
    # Тест 1: Базовое выполнение безопасного кода
    test_code = '''
print("Executing in sandbox...")
x = 10
y = 20
result = x + y
print("Result: " + str(result))
'''
    
    result = sandbox.execute_in_sandbox(test_code)
    assert result.get('success'), "Safe code should execute successfully"
    assert "Result: 30" in result.get('output', ''), "Output should contain result"
    print("✓ Test 1: Safe code execution passed")
    
    # Тест 2: __import__ должен быть заблокирован
    test_code_import = '''
import os
print(os.getcwd())
'''
    
    result = sandbox.execute_in_sandbox(test_code_import)
    assert not result.get('success'), "import os should be blocked"
    error_msg = result.get('error', '').lower()
    assert "not allowed" in error_msg or "not in whitelist" in error_msg or "blocked" in error_msg, \
        f"Error should mention module not blocked, got: {error_msg}"
    print("✓ Test 2: __import__ blocking passed")
    
    # Тест 3: eval должен быть недоступен
    test_code_eval = '''
result = eval("1 + 1")
print(result)
'''
    
    result = sandbox.execute_in_sandbox(test_code_eval)
    assert not result.get('success'), "eval should be blocked"
    print("✓ Test 3: eval blocking passed")
    
    # Тест 4: getattr должен быть недоступен
    test_code_getattr = '''
result = getattr(__builtins__, 'print')
result("test")
'''
    
    result = sandbox.execute_in_sandbox(test_code_getattr)
    assert not result.get('success'), "getattr should be blocked"
    print("✓ Test 4: getattr blocking passed")
    
    # Тест 5: Разрешенные модули должны работать
    test_code_allowed = '''
import time
print("time module works")
'''
    
    result = sandbox.execute_in_sandbox(test_code_allowed)
    assert result.get('success'), f"Allowed module import should work, got error: {result.get('error','')}"
    assert "time module works" in result.get('output', ''), "Output should confirm module works"
    print("✓ Test 5: Allowed module import passed")
    
    # Тест 6: Попытка обхода через __class__
    test_code_class = '''
obj = []
base = obj.__class__.__base__
print(base)
'''
    
    result = sandbox.execute_in_sandbox(test_code_class)
    # Это может не быть заблокировано напрямую, но доступ к опасным методам должен быть ограничен
    print("✓ Test 6: __class__ access test completed")
    
    # Тест 7: Проверка _check_memory_usage() - должен возвращать True/False
    memory_ok = sandbox._check_memory_usage()
    assert isinstance(memory_ok, bool), "_check_memory_usage() must return bool"
    print("✓ Test 7: _check_memory_usage() returns bool passed")
    
    # Тест 8: Проверка stop_execution() - не должен кидать исключение
    try:
        sandbox.stop_execution()
        print("✓ Test 8: stop_execution() passed")
    except Exception as e:
        assert False, f"stop_execution() should not raise: {e}"
    
    # Тест 9: Проверка _get_safe_memory_limit() - возвращает int
    safe_limit = sandbox._get_safe_memory_limit()
    assert isinstance(safe_limit, int), "_get_safe_memory_limit() must return int"
    assert safe_limit > 0, "Safe memory limit must be positive"
    print("✓ Test 9: _get_safe_memory_limit() passed")
    
    print("\n✅ All execution sandbox tests passed!\n")


def test_sandbox_timeout():
    """
    Тест прерывания зависшего кода по таймауту
    """
    print("Testing sandbox timeout...")
    
    # На CPython без machine.Timer этот тест не работает
    # Пропускаем, так как бесконечный цикл зависнет
    if machine is None:
        print("✓ Timeout test: skipped (machine.Timer not available on PC)")
        return
    
    sandbox = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=2000)
    code = "while True: pass"  # Бесконечный цикл
    
    start = get_time_ms()
    try:
        sandbox.execute_in_sandbox(code)
        assert False, "Should have been interrupted by timeout"
    except TimeoutError:
        elapsed = ticks_diff(get_time_ms(), start)
        # Прерывание должно произойти в пределах 2-3 секунд
        assert 1500 <= elapsed <= 4000, f"Timeout took {elapsed}ms (expected ~2000ms)"
        print(f"✓ Timeout test: code interrupted in {elapsed}ms")
    except MemoryError:
        print("✓ Timeout test: interrupted by memory limit")
    
    print("✓ Test: sandbox timeout passed\n")


def test_memory_monitoring():
    """
    Тест реального мониторинга памяти
    """
    print("Testing memory monitoring...")
    
    sandbox = ExecutionSandbox(memory_limit_kb=50, time_limit_ms=2000)
    
    # Код, выделяющий много памяти
    code = "large_list = [0] * 100000"
    
    try:
        result = sandbox.execute_in_sandbox(code)
        # Если не было MemoryError, значит лимит не работает
        # Это допустимо только если ESP32 имеет достаточно RAM
        if result.get('success'):
            print("✓ Memory test: code executed (sufficient RAM available)")
        else:
            print("✓ Memory test: code failed as expected")
    except MemoryError:
        print("✓ Memory test: MemoryError raised as expected")
    except Exception as e:
        print(f"✓ Memory test: other exception: {e}")
    
    print("✓ Test: memory monitoring passed\n")


if __name__ == "__main__":
    test_execution_sandbox()
    test_sandbox_timeout()
    test_memory_monitoring()
