"""
ExecutionEngine - движок выполнения программ с поддержкой кэширования и горячей замены
"""

import time
import gc
from execution_sandbox import ExecutionSandbox


class ExecutionEngine:
    """
    Движок выполнения программ с поддержкой кэширования и горячей замены
    """
    
    def __init__(self, memory_limit_kb=50, time_limit_ms=5000):
        self.sandbox = ExecutionSandbox(memory_limit_kb=memory_limit_kb, time_limit_ms=time_limit_ms)
        self.compiled_programs = {}
        self.execution_contexts = {}
        self.hot_swap_enabled = True
        self.max_iterations = 10000
        self.iteration_count = 0
        
    def execute_setup(self, setup_code, globals_dict=None, locals_dict=None):
        """
        Выполнение кода инициализации
        """
        if globals_dict is None:
            globals_dict = {}
        if locals_dict is None:
            locals_dict = {}
            
        result = self.sandbox.execute_in_sandbox(setup_code, globals_dict, locals_dict)
        
        # Сохраняем контекст выполнения
        context_id = 'setup_context'
        self.execution_contexts[context_id] = {
            'globals': result.get('globals', {}),
            'locals': result.get('locals', {}),
            'timestamp': time.ticks_ms()
        }
        
        return result
        
    def execute_loop(self, loop_code, max_iterations=None, globals_dict=None, locals_dict=None):
        """
        Выполнение циклического кода
        """
        if max_iterations is None:
            max_iterations = self.max_iterations
            
        if globals_dict is None:
            # Используем глобалы из контекста установки
            globals_dict = self.execution_contexts.get('setup_context', {}).get('globals', {})
        if locals_dict is None:
            locals_dict = {}
            
        iteration_count = 0
        start_time = time.ticks_ms()
        
        while iteration_count < max_iterations:
            # Проверяем лимит времени
            if time.ticks_diff(time.ticks_ms(), start_time) > self.sandbox.time_limit_seconds * 1000:
                break
                
            # Добавляем счетчик итераций в локальные переменные
            locals_dict['iteration_count'] = iteration_count
            
            try:
                result = self.sandbox.execute_in_sandbox(
                    loop_code, 
                    globals_dict, 
                    locals_dict,
                    capture_output=False
                )
                
                if not result.get('success', False):
                    print(f"Loop execution failed at iteration {iteration_count}")
                    break
                    
            except Exception as e:
                print(f"Exception during loop execution: {e}")
                break
                
            iteration_count += 1
            
            # Освобождаем память периодически
            if iteration_count % 100 == 0:
                gc.collect()
                
        self.iteration_count = iteration_count
        return {
            'iterations_completed': iteration_count,
            'execution_time_ms': time.ticks_diff(time.ticks_ms(), start_time),
            'success': True
        }
        
    def hot_swap(self, new_program):
        """
        Горячая замена программы во время выполнения
        """
        if not self.hot_swap_enabled:
            return {'success': False, 'error': 'Hot swap is disabled'}
            
        try:
            # Обновляем скомпилированную программу
            program_id = new_program.get('metadata', {}).get('id', 'default')
            self.compiled_programs[program_id] = new_program
            
            # Очищаем старые контексты выполнения
            self.execution_contexts.clear()
            
            # Выполняем новый setup
            setup_code = '\n'.join(new_program.get('setup', []))
            setup_result = self.execute_setup(setup_code)
            
            return {
                'success': True,
                'program_id': program_id,
                'setup_result': setup_result
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
            
    def cache_compiled_programs(self, program_id, executable):
        """
        Кэширование скомпилированных программ
        """
        if len(self.compiled_programs) >= 10:  # Ограничиваем размер кэша
            oldest_key = next(iter(self.compiled_programs))
            del self.compiled_programs[oldest_key]
            
        self.compiled_programs[program_id] = executable
        
    def execute_program(self, executable, max_iterations=None):
        """
        Выполнение всей программы (setup + loop)
        """
        # Выполняем setup часть
        setup_code = executable.get('setup', '')
        setup_result = self.execute_setup(setup_code)
        
        if not setup_result.get('success', False):
            return {
                'success': False,
                'error': 'Setup execution failed',
                'setup_result': setup_result
            }
            
        # Выполняем loop часть
        loop_code = executable.get('loop_logic', '')
        loop_result = self.execute_loop(loop_code, max_iterations)
        
        return {
            'success': True,
            'setup_result': setup_result,
            'loop_result': loop_result
        }
        
    def stop_execution(self):
        """
        Остановка выполнения программы
        """
        # В MicroPython нет встроенного способа остановить выполнение
        # но можно сбросить контексты выполнения
        self.execution_contexts.clear()
        gc.collect()
        
    def get_execution_stats(self):
        """
        Получение статистики выполнения
        """
        return {
            'contexts_count': len(self.execution_contexts),
            'cached_programs_count': len(self.compiled_programs),
            'current_iteration': self.iteration_count,
            'sandbox_stats': {
                'memory_limit': self.sandbox.memory_limit_bytes,
                'time_limit': self.sandbox.time_limit_seconds
            }
        }
        
    def enable_hot_swap(self, enabled=True):
        """
        Включение/отключение горячей замены
        """
        self.hot_swap_enabled = enabled
        
    def reset_engine(self):
        """
        Сброс состояния движка
        """
        self.compiled_programs.clear()
        self.execution_contexts.clear()
        self.iteration_count = 0
        self.sandbox.reset_sandbox()
        gc.collect()


# Пример использования:
if __name__ == "__main__":
    engine = ExecutionEngine(memory_limit_kb=25, time_limit_ms=2000)
    
    # Пример кода для выполнения
    setup_code = """
counter = 0
print("Setup executed")
"""
    
    loop_code = """
counter += 1
print(f"Iteration: {counter}")
if counter >= 5:
    print("Stopping...")
    break
"""
    
    print("Executing setup...")
    setup_result = engine.execute_setup(setup_code)
    print("Setup success:", setup_result.get('success'))
    
    print("\nExecuting loop...")
    loop_result = engine.execute_loop(loop_code, max_iterations=5)
    print("Loop result:", loop_result)
    
    print("\nExecution stats:", engine.get_execution_stats())