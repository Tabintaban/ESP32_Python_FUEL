"""
Основной модуль системы безопасного выполнения программ на ESP32 с MicroPython

SECURITY FIXES:
- Replaced broad exception handling with specific exceptions
- Implemented Logger class with levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Added proper error logging for each exception type
- Only use broad Exception for unexpected errors with re-raise
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


class Logger:
    """
    Класс для логирования с уровнями (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    def __init__(self, level="INFO"):
        self.levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        self.current_level = self.levels.get(level, 1)
    
    def log(self, level, message):
        """
        Логирование сообщения с заданным уровнем
        """
        if self.levels.get(level, 0) >= self.current_level:
            print(f"[{level}] {message}")
    
    def debug(self, message):
        self.log('DEBUG', message)
    
    def info(self, message):
        self.log('INFO', message)
    
    def warning(self, message):
        self.log('WARNING', message)
    
    def error(self, message):
        self.log('ERROR', message)
    
    def critical(self, message):
        self.log('CRITICAL', message)


def main():
    """
    Основная функция системы
    """
    logger = Logger(level="INFO")
    logger.info("=== ESP32 Secure Program Execution System ===")
    
    # Инициализация компонентов системы
    logger.info("Initializing system components...")
    
    try:
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
        
        logger.info("Components initialized successfully")
        
        # Генерация ключа для шифрования
        logger.info("Generating encryption key...")
        enc_key, hmac_key = crypto_manager.generate_key()
        logger.info(f"Encryption key generated: {enc_key[:8].hex()}...")
        
        # Загрузка примера программы (в реальной системе этот файл будет зашифрован)
        logger.info("Loading example LED control program...")
        
        # Для примера создадим зашифрованную версию нашего JSON-файла
        try:
            # Читаем исходный JSON файл
            with open('led_control_program.json', 'r') as f:
                program_json = f.read()
                
            # Шифруем программу
            encrypted_program = crypto_manager.encrypt_data(program_json)
            
            # Сохраняем зашифрованную версию
            with open('led_control_program.enc.json', 'w') as f:
                f.write(encrypted_program)
                
            logger.info("Program encrypted and saved as led_control_program.enc.json")
            
            # Загружаем зашифрованную программу
            loaded_program = program_loader.load_program('led_control_program.enc.json', enc_key)
            logger.info("Program loaded and validated successfully")
            
            # Извлекаем кодовые блоки
            code_blocks = json_loader.extract_code_lines(loaded_program)
            logger.info(f"Code blocks extracted: {list(code_blocks.keys())}")
            
            # Компилируем программу
            executable = compiler.build_executable(code_blocks)
            logger.info("Program compiled successfully")
            
            # Выполняем setup часть программы
            logger.info("Executing setup...")
            setup_result = engine.execute_setup(executable['setup'])
            if setup_result.get('success'):
                logger.info("Setup executed successfully")
            else:
                logger.error(f"Setup failed: {setup_result.get('error', 'Unknown error')}")
            
            # Выполняем циклическую часть программы (только несколько итераций для демонстрации)
            logger.info("Executing loop (limited to 3 iterations for demo)...")
            loop_result = engine.execute_loop(executable['loop_logic'], max_iterations=3)
            logger.info(f"Loop executed: {loop_result}")
            
            # Показываем статистику выполнения
            execution_stats = engine.get_execution_stats()
            logger.info(f"Execution stats: {execution_stats}")
            
            # Показываем статистику памяти
            memory_stats = memory_optimizer.monitor_memory_usage()
            logger.info(f"Memory stats: {memory_stats}")
            
            # Проверка давления на память
            pressure = memory_optimizer.check_memory_pressure()
            logger.info(f"Memory pressure: {pressure}")
            
            logger.info("=== System execution completed successfully ===")
            
        except FileNotFoundError as e:
            logger.warning(f"File not found: {e}. Creating a simple test program...")
            
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
            encrypted_test = crypto_manager.encrypt_data(test_program_json)
            
            with open('test_program.enc.json', 'w') as f:
                f.write(encrypted_test)
                
            logger.info("Test program created and encrypted as test_program.enc.json")
            
            # Загружаем и выполняем тестовую программу
            try:
                loaded_test = program_loader.load_program('test_program.enc.json', enc_key)
                code_blocks = json_loader.extract_code_lines(loaded_test)
                executable = compiler.build_executable(code_blocks)
                
                setup_result = engine.execute_setup(executable['setup'])
                logger.info(f"Test setup result: {setup_result.get('success')}")
                
                loop_result = engine.execute_loop(executable['loop_logic'], max_iterations=2)
                logger.info(f"Test loop result: {loop_result}")
                
            except MemoryError as e:
                logger.critical(f"Out of memory: {e}")
                gc.collect()
            except ValueError as e:
                logger.error(f"Invalid value: {e}")
            except OSError as e:
                logger.error(f"OS error: {e}")
            except Exception as e:
                logger.critical(f"Unexpected error: {type(e).__name__}: {e}")
                raise  # Пробрасываем дальше для отладки
        
        # Очистка памяти
        gc.collect()
        logger.info("Garbage collection completed. Memory freed.")
    
    except MemoryError as e:
        logger.critical(f"Memory error during initialization: {e}")
    except ValueError as e:
        logger.error(f"Value error during initialization: {e}")
    except OSError as e:
        logger.error(f"OS error during initialization: {e}")
    except Exception as e:
        logger.critical(f"Unexpected error during initialization: {e}")
        raise  # Re-raise unexpected exceptions
    

def benchmark_performance():
    """
    Функция для тестирования производительности системы
    """
    logger = Logger(level="INFO")
    logger.info("=== Performance Benchmark ===")
    
    start_time = time.ticks_ms()
    
    # Инициализация компонентов
    crypto_manager = CryptoManager()
    program_loader = ProgramLoader()
    json_loader = FastJSONLoader()
    compiler = LineBasedCompiler()
    engine = ExecutionEngine()
    
    init_time = time.ticks_diff(time.ticks_ms(), start_time)
    logger.info(f"Initialization time: {init_time}ms")
    
    # Генерация ключа
    key_gen_start = time.ticks_ms()
    key = crypto_manager.generate_key()
    key_gen_time = time.ticks_diff(time.ticks_ms(), key_gen_start)
    logger.info(f"Key generation time: {key_gen_time}ms")
    
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
        logger.info(f"Program processing time: {processing_time}ms")
        
        total_time = time.ticks_diff(time.ticks_ms(), start_time)
        logger.info(f"Total benchmark time: {total_time}ms")
        
        # Проверяем, укладываемся ли мы в требуемые 500ms
        if total_time < 500:
            logger.info("✅ Performance requirement met (< 500ms)")
        else:
            logger.warning("❌ Performance requirement not met (>= 500ms)")
            
    except FileNotFoundError as e:
        logger.warning(f"LED control program not found: {e}. Skipping processing benchmark")
    except MemoryError as e:
        logger.error(f"Memory error during benchmark: {e}")
    except OSError as e:
        logger.error(f"OS error during benchmark: {e}")


if __name__ == "__main__":
    # Выполняем основную систему
    main()
    
    # Выполняем бенчмарк
    benchmark_performance()
    
    logger = Logger(level="INFO")
    logger.info("System shutdown complete.")