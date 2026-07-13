"""
ExecutionEngine - движок выполнения программ с поддержкой кэширования и горячей замены

SECURITY FIXES:
- Added thread-based timeout mechanism for interrupting hung code
- Implemented TimeoutExecutionEngine class with _thread support
- Added proper resource cleanup after timeout
- Configurable timeout for execution limits

VULNERABILITY FIXES (v2):
- No duplicate timeout checking (delegated to sandbox.execute_in_sandbox)
- Memory checking during loop (every 10 iterations)
- Correct exception handling without breaking the loop
- External stop via stop_execution()
- Uses sandbox.execute_in_sandbox which has REAL hardware timeout (machine.Timer)

VULNERABILITY FIXES (v3) - CLEAN LOOP / FLAG-BASED STOP:
- Полностью убрана дублирующая логика таймаута в цикле. Таймаут — это
  ответственность sandbox.execute_in_sandbox (WDT + кормящий таймер).
- Цикл while прерывается, если sandbox._timeout_armed == True (внешняя
  остановка через stop_execution() ИЛИ срабатывание таймаута внутри итерации).
  Примечание: sandbox._is_running всегда False после нормального возврата из
  execute_in_sandbox (сбрасывается в finally), поэтому корректный сигнал
  остановки — именно _timeout_armed, а не _is_running.
- Проверка памяти каждые 10 итераций через gc.collect() + безопасное чтение
  gc.mem_free() (обёрнуто try/except — не падает на CPython).
- Добавлен time.sleep_ms(1) в конец каждой итерации — даёт планировщику
  MicroPython и сборщику мусора время на работу (кооперативная многозадачность).
- Безопасное чтение памяти через sandbox.memory_monitor там, где это возможно.
"""

import time
import gc
try:
    import _thread  # type: ignore # MicroPython threading support
except ImportError:
    _thread = None  # Threading not available
from execution_sandbox import ExecutionSandbox

# Совместимость с CPython и MicroPython
if hasattr(time, 'ticks_ms'):
    get_time_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def get_time_ms():
        return int(time.time() * 1000)
    def ticks_diff(end, start):
        return end - start


def _safe_mem_free():
    """
    Безопасное чтение gc.mem_free().

    Возвращает int (свободные байты) или None, если gc.mem_free() недоступен
    (CPython) или вызов упал. Используется в цикле движка для периодической
    проверки памяти без риска уронить выполнение на PC/тестах.
    """
    if not hasattr(gc, 'mem_free'):
        return None
    try:
        val = gc.mem_free()
        if val is None or val < 0:
            return None
        return int(val)
    except Exception:
        return None


class ExecutionEngine:
    """
    Движок выполнения программ с поддержкой кэширования и горячей замены
    Выполнение кода с РЕАЛЬНЫМ прерыванием по таймауту через sandbox.execute_in_sandbox
    """
    
    def __init__(self, memory_limit_kb=50, time_limit_ms=5000):
        self.sandbox = ExecutionSandbox(memory_limit_kb=memory_limit_kb, time_limit_ms=time_limit_ms)
        self.compiled_programs = {}
        self.execution_contexts = {}
        self.hot_swap_enabled = True
        self.max_iterations = 10000
        self.iteration_count = 0
        self._loop_running = False
        
    def execute_setup(self, setup_code, globals_dict=None, locals_dict=None):
        """
        Выполнение кода инициализации с опциональным таймаутом
        Таймаут обрабатывается внутри sandbox.execute_in_sandbox через machine.Timer
        """
        if globals_dict is None:
            globals_dict = {}
        if locals_dict is None:
            locals_dict = {}
        
        try:
            result = self.sandbox.execute_in_sandbox(setup_code, globals_dict, locals_dict)
        except TimeoutError as e:
            result = {'success': False, 'error': str(e)}
        except MemoryError as e:
            result = {'success': False, 'error': str(e)}
        except Exception as e:
            result = {'success': False, 'error': str(e)}
        
        # Сохраняем контекст выполнения
        context_id = 'setup_context'
        self.execution_contexts[context_id] = {
            'globals': result.get('globals', {}),
            'locals': result.get('locals', {}),
            'timestamp': get_time_ms()
        }
        
        return result
        
    def execute_loop(self, loop_code, max_iterations=None, globals_dict=None, locals_dict=None):
        """
        Выполнение циклического кода.

        Таймаут — это ответственность sandbox.execute_in_sandbox (WDT + кормящий
        таймер внутри песочницы). Здесь мы НЕ дублируем логику таймаута.

        Ключевые точки выхода из цикла:
          1. Достигнуто max_iterations.
          2. sandbox._timeout_armed == True или self._loop_running == False —
             внешняя остановка (stop_execution()) ИЛИ таймаут внутри предыдущей
             итерации. Проверяется в НАЧАЛЕ итерации (до sandbox, который
             сбрасывает _timeout_armed при запуске).
          3. Критический уровень памяти (проверка каждые 10 итераций).
          4. Итерация вернула неуспех (timeout/memory_error или иная ошибка).
        """
        if max_iterations is None:
            max_iterations = self.max_iterations

        if globals_dict is None:
            # Используем глобалы из контекста установки
            globals_dict = self.execution_contexts.get('setup_context', {}).get('globals', {})
        if locals_dict is None:
            locals_dict = {}

        self._loop_running = True
        iteration_count = 0
        start_time = get_time_ms()

        # === ПРОВЕРКА ПАМЯТИ ПЕРЕД НАЧАЛОМ ЦИКЛА (безопасная) ===
        # gc.mem_free() доступен только в MicroPython; на CPython его нет.
        gc.collect()
        free_mem_before = _safe_mem_free()
        if free_mem_before is not None and free_mem_before < 10000:
            # Минимум 10KB свободной памяти для запуска цикла.
            self._loop_running = False
            raise MemoryError(
                "Insufficient memory to start loop: only %d bytes free" % free_mem_before
            )

        while iteration_count < max_iterations and self._loop_running:
            # === ПРОВЕРКА ВНЕШНЕЙ ОСТАНОВКИ / ТАЙМАУТА (в начале итерации) ===
            # _timeout_armed устанавливается в True только при:
            #   - срабатывании таймаута внутри предыдущей итерации sandbox;
            #   - вызове stop_execution() извне.
            # Проверяем ДО вызова sandbox, потому что execute_in_sandbox
            # сбрасывает _timeout_armed=False в своём try-блоке при запуске.
            # Также проверяем собственный флаг движка (на случай, если движок
            # остановили напрямую, минуя sandbox).
            if getattr(self.sandbox, '_timeout_armed', False) or not self._loop_running:
                self._loop_running = False
                break

            # === ПЕРИОДИЧЕСКАЯ ПРОВЕРКА ПАМЯТИ (каждые 10 итераций) ===
            if iteration_count % 10 == 0:
                gc.collect()
                free_mem = _safe_mem_free()
                if free_mem is not None and free_mem < 5000:
                    # Критический уровень 5KB — аварийный выход.
                    self._loop_running = False
                    raise MemoryError(
                        "Memory exhausted: only %d bytes free" % free_mem
                    )

            # Добавляем счетчик итераций в локальные переменные (доступен коду).
            locals_dict['iteration_count'] = iteration_count

            # === ВЫЗОВ ПЕСОЧНИЦЫ (таймаут обрабатывается внутри) ===
            try:
                result = self.sandbox.execute_in_sandbox(
                    loop_code,
                    globals_dict,
                    locals_dict,
                    capture_output=False
                )

                if not result.get('success', False):
                    # Итерация завершилась с ошибкой. Различаем таймаут/память
                    # (нужно прервать цикл) от обычной ошибки кода (логируем и выходим).
                    if result.get('timeout') or result.get('memory_error'):
                        self._loop_running = False
                        break
                    print("Loop execution failed at iteration %d" % iteration_count)
                    break

            except TimeoutError:
                # Sandbox прервал выполнение по таймауту.
                self._loop_running = False
                raise
            except MemoryError:
                # Sandbox обнаружил критический уровень памяти.
                self._loop_running = False
                raise
            except Exception as e:
                # Логируем, но продолжаем цикл для устойчивости.
                print("Iteration %d error: %s" % (iteration_count, e))

            iteration_count += 1

            # === ПАУЗА ДЛЯ ПЛАНИРОВЩИКА И GC ===
            # Даём планировщику MicroPython и сборщику мусора время на работу
            # (кооперативная многозадачность). sleep_ms(1) достаточно, чтобы
            # позволить фоновым задачам (включая ISR таймера WDT) отработать.
            try:
                time.sleep_ms(1)
            except Exception:
                pass

        self._loop_running = False
        self.iteration_count = iteration_count
        return {
            'iterations_completed': iteration_count,
            'execution_time_ms': ticks_diff(get_time_ms(), start_time),
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
        Остановка выполнения программы извне
        """
        self._loop_running = False
        self.sandbox.stop_execution()  # Вызовет Watchdog сброс при необходимости
        
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
        self._loop_running = False
        self.compiled_programs.clear()
        self.execution_contexts.clear()
        self.iteration_count = 0
        self.sandbox.reset_sandbox()
        gc.collect()
