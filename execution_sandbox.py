"""
ExecutionSandbox - класс для безопасного выполнения кода в ограниченной среде
"""

import sys
import gc
try:
    from io import StringIO
except ImportError:
    # Для MicroPython используем альтернативу
    StringIO = None

import time


class ExecutionSandbox:
    """
    Класс для безопасного выполнения кода в ограниченной среде
    """
    
    def __init__(self, memory_limit_kb=50, time_limit_ms=5000):
        self.memory_limit_bytes = memory_limit_kb * 1024
        self.time_limit_seconds = time_limit_ms / 1000.0
        self.safe_builtins = self._get_safe_builtins()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        self.original_modules = sys.modules.copy()
        
    def _get_safe_builtins(self):
        """
        Получение списка безопасных встроенных функций
        """
        safe_builtins = {}
        
        # Разрешенные встроенные функции
        allowed_builtins = [
            'abs', 'all', 'any', 'bool', 'chr', 'dict', 'dir', 'divmod',
            'enumerate', 'filter', 'float', 'format', 'frozenset', 'hasattr',
            'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass', 'iter',
            'len', 'list', 'map', 'max', 'min', 'next', 'object', 'oct',
            'ord', 'pow', 'range', 'repr', 'reversed', 'round', 'set',
            'slice', 'sorted', 'str', 'sum', 'super', 'tuple', 'type',
            'zip', '__import__', 'bytes', 'bytearray', 'callable', 'complex',
            'getattr', 'isinstance', 'issubclass', 'setattr', 'vars'
        ]
        
        for builtin_name in allowed_builtins:
            if hasattr(__builtins__, builtin_name):
                safe_builtins[builtin_name] = getattr(__builtins__, builtin_name)
                
        return safe_builtins
        
    def execute_in_sandbox(self, code, globals_dict=None, locals_dict=None, capture_output=True):
        """
        Выполнение кода в песочнице
        """
        if globals_dict is None:
            globals_dict = {}
        if locals_dict is None:
            locals_dict = {}
            
        # Ограничение времени выполнения
        start_time = time.ticks_ms()
        
        # Подготовка безопасного окружения
        safe_globals = {
            '__builtins__': self.safe_builtins,
            '__name__': '__sandbox__',
            '__doc__': None,
        }
        safe_globals.update(globals_dict)
        
        # Добавляем разрешенные модули
        self._add_allowed_modules(safe_globals)
        
        # Захват вывода
        if StringIO is not None and capture_output:
            captured_output = StringIO()
            captured_error = StringIO()
        else:
            captured_output = self.original_stdout if not capture_output else None
            captured_error = self.original_stderr if not capture_output else None
        
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            # Перенаправление вывода
            if capture_output and StringIO is not None:
                sys.stdout = captured_output
                sys.stderr = captured_error
            
            # Компиляция кода
            compiled_code = compile(code, '<sandbox>', 'exec')
            
            # Выполнение кода
            exec(compiled_code, safe_globals, locals_dict)
            
            # Проверка времени выполнения
            elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000.0
            if elapsed > self.time_limit_seconds:
                raise TimeoutError(f"Execution exceeded time limit of {self.time_limit_seconds}s")
                
            # Проверка использования памяти
            if self._check_memory_usage():
                raise MemoryError(f"Memory usage exceeded limit of {self.memory_limit_bytes} bytes")
                
        except Exception as e:
            if capture_output and StringIO is not None:
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                if captured_error:
                    captured_error.write(f"Error during execution: {str(e)}")
                return {'output': captured_output.getvalue() if captured_output else "",
                       'error': captured_error.getvalue() if captured_error else str(e),
                       'success': False}
            else:
                raise e
        finally:
            # Восстановление стандартных потоков
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
        result = {
            'globals': safe_globals,
            'locals': locals_dict,
            'success': True
        }
        
        if capture_output and StringIO is not None:
            result['output'] = captured_output.getvalue() if captured_output else ""
            result['error'] = captured_error.getvalue() if captured_error else ""
        elif capture_output:
            # Для случая, когда StringIO недоступен, но capture_output = True
            result['output'] = ""
            result['error'] = ""
            
        return result
        
    def _add_allowed_modules(self, globals_dict):
        """
        Добавление разрешенных модулей в глобальное окружение
        """
        # Разрешенные модули для ESP32
        allowed_modules = [
            'machine', 'time', 'math', 'struct', 'sys', 'gc', 'json',
            '_thread', 'select', 'socket', 'ssl', 'network', 'uos'
        ]
        
        for module_name in allowed_modules:
            try:
                # Импортируем модуль и добавляем в глобальное пространство
                module = __import__(module_name)
                globals_dict[module_name] = module
            except ImportError:
                # Модуль недоступен, пропускаем
                pass
                
    def _check_memory_usage(self):
        """
        Проверка использования памяти
        """
        try:
            # В MicroPython нет встроенного способа получения текущего использования памяти
            # Поэтому просто вызываем сборщик мусора и возвращаем False
            gc.collect()
            return False
        except:
            return False
            
    def limit_resources(self, memory_limit_kb=None, time_limit_ms=None):
        """
        Установка ограничений ресурсов
        """
        if memory_limit_kb is not None:
            self.memory_limit_bytes = memory_limit_kb * 1024
        if time_limit_ms is not None:
            self.time_limit_seconds = time_limit_ms / 1000.0
            
    def monitor_execution_time(self, start_time):
        """
        Мониторинг времени выполнения
        """
        elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000.0
        return elapsed > self.time_limit_seconds
        
    def stop_execution(self):
        """
        Принудительная остановка выполнения
        """
        # В MicroPython нет встроенной возможности прервать выполнение
        # Можно только завершить выполнение через исключение
        raise KeyboardInterrupt("Execution stopped by sandbox")
        
    def execute_with_timeout(self, code, timeout_sec, globals_dict=None, locals_dict=None):
        """
        Выполнение кода с таймаутом
        """
        start_time = time.ticks_ms()
        
        result = self.execute_in_sandbox(
            code, 
            globals_dict=globals_dict, 
            locals_dict=locals_dict,
            capture_output=True
        )
        
        elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000.0
        
        if elapsed > timeout_sec:
            result['timeout'] = True
            result['success'] = False
        else:
            result['execution_time'] = elapsed
            
        return result
        
    def reset_sandbox(self):
        """
        Сброс состояния песочницы
        """
        # Восстановление оригинальных потоков
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
        
        # Восстановление оригинальных модулей
        sys.modules.clear()
        sys.modules.update(self.original_modules)
        
        # Очистка памяти
        gc.collect()


# Пример использования:
if __name__ == "__main__":
    sandbox = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=1000)
    
    # Простой код для тестирования
    test_code = '''
print("Executing in sandbox...")
x = 10
y = 20
result = x + y
print("Result: " + str(result))
'''
    
    result = sandbox.execute_in_sandbox(test_code)
    print("Output:", result.get('output'))
    print("Success:", result.get('success'))
    print("Globals keys:", [k for k in result.get('globals', {}).keys() if not k.startswith('__')])