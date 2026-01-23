"""
PerformanceTests - модуль для измерения производительности системы
"""

import time
import gc
from crypto_manager import CryptoManager
from program_loader import ProgramLoader
from fast_json_loader import FastJSONLoader
from line_compiler import LineBasedCompiler
from execution_engine import ExecutionEngine


class PerformanceTests:
    """
    Класс для тестирования производительности системы
    """
    
    def __init__(self):
        self.results = {}
        self.crypto_manager = CryptoManager()
        self.program_loader = ProgramLoader()
        self.json_loader = FastJSONLoader()
        self.compiler = LineBasedCompiler()
        self.engine = ExecutionEngine()
        
    def test_load_time(self, filepath, key):
        """
        Тестирование времени загрузки файла
        """
        start_time = time.ticks_ms()
        
        try:
            program_data = self.program_loader.load_program(filepath, key)
            load_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            return {
                'success': True,
                'time_ms': load_time,
                'program_size': len(str(program_data))
            }
        except Exception as e:
            return {
                'success': False,
                'time_ms': time.ticks_diff(time.ticks_ms(), start_time),
                'error': str(e)
            }
            
    def test_decrypt_time(self, encrypted_data, key):
        """
        Тестирование времени дешифрования
        """
        start_time = time.ticks_ms()
        
        try:
            decrypted_data = self.crypto_manager.decrypt_data(encrypted_data, key)
            decrypt_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            return {
                'success': True,
                'time_ms': decrypt_time,
                'data_size': len(decrypted_data)
            }
        except Exception as e:
            return {
                'success': False,
                'time_ms': time.ticks_diff(time.ticks_ms(), start_time),
                'error': str(e)
            }
            
    def test_compile_time(self, code_blocks):
        """
        Тестирование времени компиляции
        """
        start_time = time.ticks_ms()
        
        try:
            executable = self.compiler.build_executable(code_blocks)
            compile_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            return {
                'success': True,
                'time_ms': compile_time,
                'code_size': len(executable['full_code'])
            }
        except Exception as e:
            return {
                'success': False,
                'time_ms': time.ticks_diff(time.ticks_ms(), start_time),
                'error': str(e)
            }
            
    def test_execution_time(self, executable, iterations=100):
        """
        Тестирование времени выполнения
        """
        start_time = time.ticks_ms()
        
        try:
            result = self.engine.execute_program(executable, max_iterations=iterations)
            execution_time = time.ticks_diff(time.ticks_ms(), start_time)
            
            return {
                'success': result['success'],
                'time_ms': execution_time,
                'iterations': iterations,
                'avg_per_iteration_ms': execution_time / iterations if iterations > 0 else 0
            }
        except Exception as e:
            return {
                'success': False,
                'time_ms': time.ticks_diff(time.ticks_ms(), start_time),
                'error': str(e)
            }
            
    def test_memory_usage(self):
        """
        Тестирование использования памяти
        """
        # В MicroPython нет точного способа измерения использования памяти
        # поэтому используем косвенные методы
        gc.collect()
        
        # Состояние до
        before_collect = 0  # Заглушка
        
        # Создаем нагрузку
        temp_data = []
        for i in range(100):
            temp_data.append(bytearray(100))  # Создаем 100 байтовые массивы
            
        gc.collect()
        
        # Состояние после
        after_collect = 0  # Заглушка
        
        # Очищаем
        del temp_data
        gc.collect()
        
        return {
            'memory_test_completed': True,
            'gc_collected': True  # Информация о том, что сборка мусора выполнена
        }
        
    def run_full_benchmark(self, program_filepath, encryption_key):
        """
        Запуск полного бенчмарка
        """
        print("Starting full performance benchmark...")
        
        results = {}
        
        # 1. Тест дешифрования
        print("Testing decryption...")
        with open(program_filepath, 'r') as f:
            encrypted_data = f.read()
        results['decrypt'] = self.test_decrypt_time(encrypted_data, encryption_key)
        print(f"Decryption time: {results['decrypt']['time_ms']}ms")
        
        # 2. Тест загрузки
        print("Testing load...")
        results['load'] = self.test_load_time(program_filepath, encryption_key)
        print(f"Load time: {results['load']['time_ms']}ms")
        
        # 3. Тест компиляции
        print("Testing compilation...")
        program_data = self.program_loader.load_program(program_filepath, encryption_key)
        code_blocks = self.json_loader.extract_code_lines(program_data)
        results['compile'] = self.test_compile_time(code_blocks)
        print(f"Compilation time: {results['compile']['time_ms']}ms")
        
        # 4. Тест выполнения
        print("Testing execution...")
        executable = self.compiler.build_executable(code_blocks)
        results['execution'] = self.test_execution_time(executable, iterations=10)
        print(f"Execution time: {results['execution']['time_ms']}ms for {results['execution']['iterations']} iterations")
        
        # 5. Тест памяти
        print("Testing memory usage...")
        results['memory'] = self.test_memory_usage()
        print("Memory test completed")
        
        # Рассчитываем общее время
        total_time = (
            results['decrypt']['time_ms'] +
            results['load']['time_ms'] +
            results['compile']['time_ms'] +
            results['execution']['time_ms']
        )
        
        results['total'] = {
            'time_ms': total_time,
            'within_500ms': total_time < 500
        }
        
        print(f"\nTotal benchmark time: {total_time}ms")
        print(f"Within 500ms requirement: {total_time < 500}")
        
        # Проверяем требования к производительности
        performance_summary = {
            'load_time_ok': results['load']['time_ms'] < 100,
            'decrypt_time_ok': results['decrypt']['time_ms'] < 150,
            'compile_time_ok': results['compile']['time_ms'] < 100,
            'execution_time_ok': results['execution']['time_ms'] < 150,
            'total_time_ok': total_time < 500,
            'detailed_results': results
        }
        
        return performance_summary
        
    def generate_report(self, benchmark_results):
        """
        Генерация отчета о производительности
        """
        report = []
        report.append("=== PERFORMANCE BENCHMARK REPORT ===")
        report.append("")
        
        results = benchmark_results['detailed_results']
        
        report.append(f"Load time: {results['load']['time_ms']}ms ({'OK' if results['load']['time_ms'] < 100 else 'FAIL'})")
        report.append(f"Decrypt time: {results['decrypt']['time_ms']}ms ({'OK' if results['decrypt']['time_ms'] < 150 else 'FAIL'})")
        report.append(f"Compile time: {results['compile']['time_ms']}ms ({'OK' if results['compile']['time_ms'] < 100 else 'FAIL'})")
        report.append(f"Execution time: {results['execution']['time_ms']}ms ({'OK' if results['execution']['time_ms'] < 150 else 'FAIL'})")
        report.append(f"Total time: {results['total']['time_ms']}ms ({'OK' if results['total']['time_ms'] < 500 else 'FAIL'})")
        report.append("")
        
        overall_status = "PASSED" if results['total']['within_500ms'] else "FAILED"
        report.append(f"Overall performance: {overall_status}")
        report.append("")
        
        # Проверка использования памяти
        report.append("Memory usage: Tested (GC performed)")
        report.append("")
        
        report.append("=== END OF REPORT ===")
        
        return "\n".join(report)


# Функция для запуска тестов производительности
def run_performance_tests():
    """
    Функция для запуска тестов производительности
    """
    print("Initializing performance tests...")
    
    tests = PerformanceTests()
    
    # Генерируем ключ для тестирования
    key = tests.crypto_manager.generate_key()
    
    # Проверяем наличие тестовой программы
    import os
    if os.path.exists('led_control_program.enc.json'):
        program_file = 'led_control_program.enc.json'
    elif os.path.exists('test_program.enc.json'):
        program_file = 'test_program.enc.json'
    else:
        print("No encrypted program file found. Creating one for testing...")
        
        # Создаем тестовую программу
        from lightweight_security import LightweightSecurity
        security = LightweightSecurity()
        
        test_program = {
            "metadata": {
                "version": "1.0",
                "signature": security.sign_data("test_program").hex(),
                "timestamp": "2023-01-01T00:00:00Z",
                "checksum": tests.crypto_manager.hash_data(str({"imports": ["import time"], "functions": [], "setup": ["print('Setup')"], "loop_logic": ["time.sleep(0.1)"]})),
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
            "setup": ["print('Test program setup')"],
            "loop_logic": ["print('Iteration')", "time.sleep(0.1)"]
        }
        
        import json
        test_program_json = json.dumps(test_program)
        encrypted_test = tests.crypto_manager.encrypt_data(test_program_json, key)
        
        with open('test_program.enc.json', 'w') as f:
            f.write(encrypted_test)
            
        program_file = 'test_program.enc.json'
    
    print(f"Running benchmark on {program_file}...")
    
    # Запускаем полный бенчмарк
    benchmark_results = tests.run_full_benchmark(program_file, key)
    
    # Генерируем отчет
    report = tests.generate_report(benchmark_results)
    print(report)
    
    return benchmark_results


if __name__ == "__main__":
    run_performance_tests()