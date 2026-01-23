"""
Основной модуль системы безопасного выполнения программ на ESP32 с MicroPython
"""

import time
import gc
from crypto_manager import CryptoManager
from object_factory import ObjectFactory
from execution_sandbox import ExecutionSandbox
from program_loader import ProgramLoader
from fast_json_loader import FastJSONLoader
from line_compiler import LineBasedCompiler
from execution_engine import ExecutionEngine
from lightweight_security import LightweightSecurity
from memory_optimizer import MemoryOptimizer


def main():
    """
    Основная функция системы
    """
    print("=== ESP32 Secure Program Execution System ===")
    
    # Инициализация компонентов системы
    print("Initializing system components...")
    
    # 1. Криптографический менеджер
    crypto_manager = CryptoManager()
    
    # 2. Загрузчик программ
    program_loader = ProgramLoader()
    
    # 3. Быстрый JSON-лоадер
    json_loader = FastJSONLoader()
    
    # 4. Компилятор строкового кода
    compiler = LineBasedCompiler()
    
    # 5. Движок выполнения
    engine = ExecutionEngine(memory_limit_kb=25, time_limit_ms=2000)
    
    # 6. Менеджер памяти
    memory_optimizer = MemoryOptimizer(max_memory_kb=30)
    
    # 7. Безопасность
    security = LightweightSecurity()
    
    print("Components initialized successfully")
    
    # Генерация ключа для шифрования
    print("Generating encryption key...")
    encryption_key = crypto_manager.generate_key()
    print(f"Encryption key generated: {encryption_key[:8].hex()}...")
    
    # Загрузка примера программы (в реальной системе этот файл будет зашифрован)
    print("\nLoading example LED control program...")
    
    # Для примера создадим зашифрованную версию нашего JSON-файла
    try:
        # Читаем исходный JSON файл
        with open('led_control_program.json', 'r') as f:
            program_json = f.read()
            
        # Шифруем программу
        encrypted_program = crypto_manager.encrypt_data(program_json, encryption_key)
        
        # Сохраняем зашифрованную версию
        with open('led_control_program.enc.json', 'w') as f:
            f.write(encrypted_program)
            
        print("Program encrypted and saved as led_control_program.enc.json")
        
        # Загружаем зашифрованную программу
        loaded_program = program_loader.load_program('led_control_program.enc.json', encryption_key)
        print("Program loaded and validated successfully")
        
        # Извлекаем кодовые блоки
        code_blocks = json_loader.extract_code_lines(loaded_program)
        print(f"Code blocks extracted: {list(code_blocks.keys())}")
        
        # Компилируем программу
        executable = compiler.build_executable(code_blocks)
        print("Program compiled successfully")
        
        # Выполняем setup часть программы
        print("\nExecuting setup...")
        setup_result = engine.execute_setup(executable['setup'])
        if setup_result.get('success'):
            print("Setup executed successfully")
        else:
            print(f"Setup failed: {setup_result.get('error', 'Unknown error')}")
        
        # Выполняем циклическую часть программы (только несколько итераций для демонстрации)
        print("\nExecuting loop (limited to 3 iterations for demo)...")
        loop_result = engine.execute_loop(executable['loop_logic'], max_iterations=3)
        print(f"Loop executed: {loop_result}")
        
        # Показываем статистику выполнения
        execution_stats = engine.get_execution_stats()
        print(f"\nExecution stats: {execution_stats}")
        
        # Показываем статистику памяти
        memory_stats = memory_optimizer.monitor_memory_usage()
        print(f"Memory stats: {memory_stats}")
        
        # Проверка давления на память
        pressure = memory_optimizer.check_memory_pressure()
        print(f"Memory pressure: {pressure}")
        
        print("\n=== System execution completed successfully ===")
        
    except FileNotFoundError:
        print("Warning: led_control_program.json not found. Creating a simple test program...")
        
        # Создаем простую тестовую программу
        test_program = {
            "metadata": {
                "version": "1.0",
                "signature": security.sign_data("test_program").hex(),
                "timestamp": "2023-01-01T00:00:00Z",
                "checksum": crypto_manager.hash_data(str({"imports": [], "functions": [], "setup": ["print('Test program')"], "loop_logic": ["print('Loop iteration')"]})),
                "author": "Test",
                "description": "Simple test program"
            },
            "config": {
                "runtime_limit_ms": 1000,
                "memory_limit_kb": 10,
                "permissions": ["time"]
            },
            "imports": ["import time"],
            "functions": [],
            "setup": ["print('Test program setup executed')"],
            "loop_logic": ["print('Test loop iteration')", "time.sleep(0.5)"]
        }
        
        # Шифруем тестовую программу
        test_program_json = str(test_program).replace("'", '"')  # Простая конвертация в JSON
        encrypted_test = crypto_manager.encrypt_data(test_program_json, encryption_key)
        
        with open('test_program.enc.json', 'w') as f:
            f.write(encrypted_test)
            
        print("Test program created and encrypted as test_program.enc.json")
        
        # Загружаем и выполняем тестовую программу
        try:
            loaded_test = program_loader.load_program('test_program.enc.json', encryption_key)
            code_blocks = json_loader.extract_code_lines(loaded_test)
            executable = compiler.build_executable(code_blocks)
            
            setup_result = engine.execute_setup(executable['setup'])
            print(f"Test setup result: {setup_result.get('success')}")
            
            loop_result = engine.execute_loop(executable['loop_logic'], max_iterations=2)
            print(f"Test loop result: {loop_result}")
            
        except Exception as e:
            print(f"Error executing test program: {e}")
    
    # Очистка памяти
    gc.collect()
    print(f"\nGarbage collection completed. Memory freed.")
    

def benchmark_performance():
    """
    Функция для тестирования производительности системы
    """
    print("\n=== Performance Benchmark ===")
    
    start_time = time.ticks_ms()
    
    # Инициализация компонентов
    crypto_manager = CryptoManager()
    program_loader = ProgramLoader()
    json_loader = FastJSONLoader()
    compiler = LineBasedCompiler()
    engine = ExecutionEngine()
    
    init_time = time.ticks_diff(time.ticks_ms(), start_time)
    print(f"Initialization time: {init_time}ms")
    
    # Генерация ключа
    key_gen_start = time.ticks_ms()
    key = crypto_manager.generate_key()
    key_gen_time = time.ticks_diff(time.ticks_ms(), key_gen_start)
    print(f"Key generation time: {key_gen_time}ms")
    
    # Загрузка и обработка тестовой программы
    processing_start = time.ticks_ms()
    
    try:
        with open('led_control_program.json', 'r') as f:
            program_json = f.read()
            
        encrypted = crypto_manager.encrypt_data(program_json, key)
        loaded = program_loader.load_program('led_control_program.enc.json', key)
        code_blocks = json_loader.extract_code_lines(loaded)
        executable = compiler.build_executable(code_blocks)
        
        processing_time = time.ticks_diff(time.ticks_ms(), processing_start)
        print(f"Program processing time: {processing_time}ms")
        
        total_time = time.ticks_diff(time.ticks_ms(), start_time)
        print(f"Total benchmark time: {total_time}ms")
        
        # Проверяем, укладываемся ли мы в требуемые 500ms
        if total_time < 500:
            print("✅ Performance requirement met (< 500ms)")
        else:
            print("❌ Performance requirement not met (>= 500ms)")
            
    except FileNotFoundError:
        print("LED control program not found, skipping processing benchmark")


if __name__ == "__main__":
    # Выполняем основную систему
    main()
    
    # Выполняем бенчмарк
    benchmark_performance()
    
    print("\nSystem shutdown complete.")