"""
Unit tests for memory_optimizer module
"""
import sys
sys.path.insert(0, '..')

from memory_optimizer import MemoryOptimizer


def test_memory_optimizer():
    """
    Unit-тесты для MemoryOptimizer
    """
    print("Testing MemoryOptimizer...")
    
    optimizer = MemoryOptimizer(max_memory_kb=25)
    
    # Тест 1: Предварительное выделение буферов
    buffers_config = {
        'input_buffer': 1024,
        'output_buffer': 1024,
        'temp_buffer': 512
    }
    
    buffers = optimizer.preallocate_buffers(buffers_config)
    assert len(buffers) == 3, "Should allocate 3 buffers"
    print("✓ Test 1: Buffer allocation passed")
    
    # Тест 2: Проверка памяти перед выполнением
    try:
        optimizer.check_before_execution(estimated_bytes=1000)
        print("✓ Test 2: Pre-execution memory check passed")
    except MemoryError:
        print("✓ Test 2: Pre-execution memory check (insufficient memory)")
    
    # Тест 3: Проверка памяти во время выполнения
    try:
        free = optimizer.check_during_execution()
        assert isinstance(free, int), "Should return free memory as int"
        print("✓ Test 3: During-execution memory check passed")
    except MemoryError:
        print("✓ Test 3: During-execution memory check (critical level)")
    
    # Тест 4: Детальная статистика памяти
    stats = optimizer.get_memory_stats()
    assert 'free' in stats, "Stats should include free memory"
    assert 'allocated' in stats, "Stats should include allocated memory"
    assert 'total' in stats, "Stats should include total memory"
    print("✓ Test 4: Detailed memory stats passed")
    
    # Тест 5: Проверка давления на память
    pressure = optimizer.check_memory_pressure()
    assert 'pressure_ratio' in pressure, "Pressure should include ratio"
    assert 'is_critical' in pressure, "Pressure should include critical flag"
    print("✓ Test 5: Memory pressure check passed")
    
    # Тест 6: Очистка памяти
    cleanup_result = optimizer.cleanup_cache()
    assert 'cleaned_caches' in cleanup_result, "Cleanup should report cleaned caches"
    print("✓ Test 6: Memory cleanup passed")
    
    print("\n✅ All memory optimizer tests passed!\n")


if __name__ == "__main__":
    test_memory_optimizer()
