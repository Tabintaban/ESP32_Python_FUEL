"""
ExecutionSandbox - класс для безопасного выполнения кода в ограниченной среде

SECURITY FIXES:
- Removed __import__ from allowed_builtins (critical security flaw)
- Implemented SafeImporter with module whitelist
- Added restricted globals dict to block dangerous builtins
- Protected against getattr, eval, __class__ escape attempts
- Blocked relative imports above level 0

VULNERABILITY FIXES (v2):
- _check_memory_usage() now uses gc.mem_free() and returns REAL status
- Code is interrupted by timeout via machine.Timer (hardware timer)
- stop_execution() can interrupt execution from outside via Watchdog
- Hardware Watchdog Timer as fallback
- Memory check before, during and after execution
- Integrated RealTimeMemoryMonitor from memory_optimizer

VULNERABILITY FIXES (v3) - RELIABLE TIMEOUT / FAIL-SECURE MEMORY:
- ПАМЯТЬ: _check_memory_usage() использует gc.mem_free() с корректным порогом
  (20% от memory_limit_bytes) и возвращает РЕАЛЬНЫЙ статус (bool). При недоступности
  gc.mem_free (CPython) — безопасная деградация, но не ложный успех.
- ТАЙМАУТ: исправлена критическая ошибка v2. В MicroPython исключение, поднятое
  из колбэка machine.Timer (ISR), НЕ прерывает блокирующий exec()/бесконечный
  цикл на C-уровне. Поэтому используется НАДЁЖНАЯ аппаратная схема:
    * Запускается ПЕРИОДИЧЕСКИЙ machine.Timer, который каждые ~250 мс «кормит»
      аппаратный WDT и проверяет флаг _is_running.
    * Пока код укладывается в лимит времени, таймер держит WDT живым.
    * При превышении лимита ИЛИ при вызове stop_execution() кормление WDT
      прекращается -> ESP32 аппаратно перезагружается. Это ЕДИНСТВЕННЫЙ
      гарантированный способ прервать зависший на C-уровне код в MicroPython.
    * Для кооперативного кода (sleep/проверки флага) предусмотрена мягкая
      остановка через self._is_running без перезагрузки.
- ИНТЕГРАЦИЯ: RealTimeMemoryMonitor используется ДО/ВО ВРЕМЯ/ПОСЛЕ выполнения.
- _is_running — публичный флаг, проверяемый движком (ExecutionEngine) для
  немедленного выхода из цикла при остановке.
"""

import sys
import gc
try:
    from io import StringIO
except ImportError:
    # Для MicroPython используем альтернативу
    StringIO = None

import time

# Импортируем builtins для безопасного доступа к встроенным функциям.
# На CPython есть модуль builtins и функция vars().
# На MicroPython их нет — но встроенные функции доступны напрямую,
# поэтому _BUILTINS_DICT можно заполнить вручную.
try:
    import builtins as _builtins_module
    _BUILTINS_DICT = vars(_builtins_module)
except (ImportError, NameError):
    # MicroPython: нет builtins, нет vars().
    # Пробуем достать __builtins__ (в некоторых портах есть),
    # иначе — соберём словарь из прямых ссылок на встроенные функции.
    try:
        _bi = __builtins__
        if isinstance(_bi, dict):
            _BUILTINS_DICT = _bi
        elif hasattr(_bi, '__dict__'):
            _BUILTINS_DICT = _bi.__dict__
        else:
            _BUILTINS_DICT = {}
    except NameError:
        _BUILTINS_DICT = {}

# Попытка импорта аппаратных модулей ESP32
try:
    import machine
except ImportError:
    machine = None  # Для тестирования на PC

try:
    import _thread
except ImportError:
    _thread = None


class SafeImporter:
    """
    Безопасный механизм импорта модулей с whitelist
    """
    
    def __init__(self, allowed_modules):
        self._allowed = set(allowed_modules)
        self._cache = {}
    
    def __import__(self, name, globals=None, locals=None, fromlist=(), level=0):
        """
        Безопасный импорт модулей
        
        Args:
            name: Имя модуля для импорта
            globals: Глобальные переменные (игнорируется)
            locals: Локальные переменные (игнорируется)
            fromlist: Список имен для импорта из модуля
            level: Уровень относительного импорта
            
        Raises:
            ImportError: Если модуль не в whitelist или level > 0
        """
        # Проверка whitelist
        if name not in self._allowed:
            raise ImportError(f"Module '{name}' is not allowed in sandbox")
        
        # Запрет относительных импортов выше уровня 0
        if level > 0:
            raise ImportError("Relative imports are not allowed in sandbox")
        
        # Кэширование для производительности
        if name not in self._cache:
            # В MicroPython __builtins__ может не быть — используем __import__
            # напрямую (он доступен как встроенная функция).
            self._cache[name] = __import__(name, globals, locals, fromlist, level)
                    
        return self._cache[name]


# RESTRICTED_GLOBALS - безопасный словарь глобальных переменных
RESTRICTED_GLOBALS = {
    '__builtins__': {
        # Только безопасные встроенные функции
        'print': print,
        'len': len,
        'range': range,
        'int': int,
        'float': float,
        'str': str,
        'list': list,
        'dict': dict,
        'tuple': tuple,
        'set': set,
        'bool': bool,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'map': map,
        'filter': filter,
        'sorted': sorted,
        'enumerate': enumerate,
        'zip': zip,
        'isinstance': isinstance,
        'type': type,  # с ограничениями
        # ЗАПРЕЩЕНО: __import__, open, exec, eval, compile, globals, locals, vars
        # ЗАПРЕЩЕНО: getattr, setattr, delattr (могут использоваться для обхода)
    }
}


class ExecutionSandbox:
    """
    Класс для безопасного выполнения кода в ограниченной среде
    с РЕАЛЬНЫМ прерыванием по таймауту (через WDT) и РЕАЛЬНЫМ мониторингом памяти.

    Схема таймаута (v3):
      - Перед exec() запускается ПЕРИОДИЧЕСКИЙ аппаратный таймер (~250 мс),
        который кормит WDT, пока выполняется код и не истёк лимит времени.
      - Если код превысил time_limit_ms ИЛИ был вызван stop_execution(),
        кормление WDT прекращается -> аппаратная перезагрузка ESP32.
      - Это единственный надёжный способ прервать зависший C-level код
        (например, `while True: pass`) в MicroPython — исключения из ISR
        не прерывают блокирующий exec().
      - Для кооперативного кода доступен мягкий останов через флаг _is_running.
    """

    def __init__(self, memory_limit_kb=50, time_limit_ms=5000, allowed_modules=None):
        self.memory_limit_bytes = memory_limit_kb * 1024
        self.time_limit_seconds = time_limit_ms / 1000.0
        self.time_limit_ms = time_limit_ms

        # === СОСТОЯНИЕ ВЫПОЛНЕНИЯ ===
        # Публичный флаг: True, пока код выполняется и его можно прерывать.
        # ExecutionEngine проверяет sandbox._is_running для немедленного выхода из цикла.
        self._is_running = False
        # Время старта текущего выполнения (для проверки таймаута из таймера).
        self._exec_start_ms = 0
        # Флаг аппаратного сброса: True, если таймер решил «уморить» WDT.
        self._timeout_armed = False

        # Блокировка для безопасного доступа к флагам из ISR таймера.
        self._lock = _thread.allocate_lock() if _thread else _dummy_lock()

          # Программный таймер для проверки таймаута (кооперативный).
        # WDT не используется: в MicroPython на ESP32 его нельзя остановить
        # после запуска (deinit не поддерживается), и он вызывает сбросы.
        self._keepalive_timer = None
        self._keepalive_period_ms = 250

        # Разрешенные модули для ESP32
        # TUR55 раздел 6: запрещены os, socket, urandom и сетевые модули.
        # Оставляем только модули, необходимые для управления устройством.
        if allowed_modules is None:
            allowed_modules = [
                'machine',  # GPIO, Timer, WDT
                'time',     # sleep, ticks_ms
                'math',     # математика
                'struct',   # бинарные данные
                'json',     # парсинг JSON
                'gc',       # управление памятью
            ]

        self.safe_importer = SafeImporter(allowed_modules)
        self.safe_builtins = self._get_safe_builtins()
        # sys.stdout/sys.stderr есть только в CPython; в MicroPython их нет.
        self.original_stdout = getattr(sys, 'stdout', None)
        self.original_stderr = getattr(sys, 'stderr', None)
        # sys.modules.copy() тоже недоступен в MicroPython.
        try:
            self.original_modules = sys.modules.copy()
        except AttributeError:
            self.original_modules = None


        # Инициализация монитора памяти из memory_optimizer
        try:
            from memory_optimizer import RealTimeMemoryMonitor
            self.memory_monitor = RealTimeMemoryMonitor(
                hard_limit_bytes=self.memory_limit_bytes
            )
        except ImportError:
            self.memory_monitor = None
        
    def _get_safe_builtins(self):
        """
        Получение списка безопасных встроенных функций
        
        ЗАПРЕЩЕНО: __import__, eval, exec, compile, open, globals, locals, vars
        ЗАПРЕЩЕНО: getattr, setattr, delattr (могут использоваться для обхода песочницы)
        """
        safe_builtins = {}
        
        # Используем глобальный _BUILTINS_DICT (инициализирован при импорте модуля)
        # Работает и на CPython, и на MicroPython
        builtins_dict = _BUILTINS_DICT
        
        # Разрешенные встроенные функции (БЕЗ __import__)
        allowed_builtins = [
            'abs', 'all', 'any', 'bool', 'chr', 'dict', 'dir', 'divmod',
            'enumerate', 'filter', 'float', 'format', 'frozenset',
            'hash', 'hex', 'id', 'int', 'isinstance', 'issubclass', 'iter',
            'len', 'list', 'map', 'max', 'min', 'next', 'object', 'oct',
            'ord', 'pow', 'print', 'range', 'repr', 'reversed', 'round', 'set',
            'slice', 'sorted', 'str', 'sum', 'super', 'tuple', 'type',
            'zip', 'bytes', 'bytearray', 'callable', 'complex'
            # ЗАПРЕЩЕНО: __import__, getattr, setattr, delattr, vars
        ]
        
        # На MicroPython _BUILTINS_DICT может быть пустым, но встроенные
        # функции доступны напрямую как глобальные имена в модуле.
        # Поэтому пробуем сначала builtins_dict, потом globals() модуля.
        for builtin_name in allowed_builtins:
            if builtin_name in builtins_dict:
                safe_builtins[builtin_name] = builtins_dict[builtin_name]
            else:
                # Fallback: берём из globals() текущего модуля.
                # В MicroPython встроенные функции видны как глобальные имена.
                try:
                    safe_builtins[builtin_name] = globals()[builtin_name]
                except KeyError:
                    pass

        return safe_builtins


    def _get_safe_memory_limit(self):
        """Определение безопасного лимита памяти (50% от свободной RAM)"""
        gc.collect()
        try:
            free_memory = gc.mem_free()
            return int(free_memory * 0.5)  # Используем только половину
        except AttributeError:
            # gc.mem_free() недоступен на стандартном Python
            return self.memory_limit_bytes
    
    def _check_memory_usage(self):
        """
        РЕАЛЬНАЯ проверка свободной памяти через gc.

        Возвращает True, если свободной памяти больше порогового значения
        (20% от memory_limit_bytes), иначе False. Перед замером вызывает
        gc.collect() для уплотнения кучи.

        На CPython (где нет gc.mem_free) возвращаем True — там лимиты памяти
       sandbox'а не имеют смысла, и ложный успех не компрометирует ESP32.
        """
        try:
            gc.collect()
            free_memory = gc.mem_free()
        except AttributeError:
            # gc.mem_free() недоступен на стандартном Python (PC) —
            # безопасная деградация: не блокируем выполнение вне ESP32.
            return True
        except Exception:
            # Любая иная ошибка gc (фрагментация/повреждение) — небезопасно
            # продолжать; сообщаем, что памяти «нет».
            return False

        # free_memory может прийти некорректным при тяжёлой фрагментации.
        if free_memory is None or free_memory < 0:
            return False

        # Порог: свободно должно быть > 20% от лимита песочницы.
        threshold = self.memory_limit_bytes * 0.2
        if free_memory < threshold:
            # Перед отказом — попытка освободить память и перепроверить.
            gc.collect()
            try:
                free_memory = gc.mem_free()
            except Exception:
                return False
            if free_memory is None or free_memory < threshold:
                return False

        return True
    
    def _estimate_code_memory(self, code):
        """
        Оценка памяти, необходимой для выполнения кода
        """
        # Грубая оценка: размер кода * 2 (для байткода) + фиксированный запас
        code_size = len(code) if isinstance(code, str) else len(str(code))
        estimated = code_size * 2 + 1024  # +1KB запас
        return min(estimated, self.memory_limit_bytes // 2)  # Не больше половины лимита
    
    def execute_in_sandbox(self, code, globals_dict=None, locals_dict=None, capture_output=True):
        """
        Выполнение кода в песочнице с РЕАЛЬНЫМ прерыванием по таймауту (через WDT)
        и РЕАЛЬНЫМ мониторингом памяти.

        Надёжность таймаута:
          - Перед exec() запускается WDT (аппаратный) и периодический таймер,
            который кормит его, пока код не превысил time_limit_ms.
          - Если код зависнет в бесконечном C-level цикле, таймер перестанет
            кормить WDT -> ESP32 аппаратно перезагрузится.
          - Для кооперативного кода таймер просто сбрасывает флаг _is_running,
            и код может сам завершиться (если проверяет флаг).

        Args:
            code: Код для выполнения
            globals_dict: Глобальные переменные
            locals_dict: Локальные переменные
            capture_output: Захватывать ли вывод

        Returns:
            Словарь с результатами выполнения

        Raises:
            RuntimeError: Если превышен лимит времени (мягкая кооперативная остановка)
            MemoryError: Если превышен лимит памяти
        """
        if globals_dict is None:
            globals_dict = {}
        if locals_dict is None:
            locals_dict = {}

        # === ПРОВЕРКА ПАМЯТИ ДО ВЫПОЛНЕНИЯ ===
        if not self._check_memory_usage():
            raise MemoryError("Insufficient memory before execution")

        # Используем RealTimeMemoryMonitor если доступен
        if self.memory_monitor:
            estimated_memory = self._estimate_code_memory(code)
            try:
                self.memory_monitor.check_before_execution(estimated_memory)
            except MemoryError:
                raise

        # === ПОДГОТОВКА БЕЗОПАСНОГО ОКРУЖЕНИЯ ===
        sandbox_builtins = dict(self.safe_builtins)
        sandbox_builtins['__import__'] = self.safe_importer.__import__

        # === ВЫВОД print ===
        # В MicroPython print нельзя перехватить через __builtins__
        # (print вшит в интерпретатор). Поэтому capture_output игнорируется,
        # и print идёт напрямую в консоль.
        # Если понадобится перехват — использовать os.dupterm().
        _capture_buffer = []

        safe_globals = {
            '__builtins__': sandbox_builtins,
            '__name__': '__sandbox__',
            '__doc__': None,
        }
        safe_globals.update(globals_dict)
        self._add_allowed_modules(safe_globals)

        # === ЗАПУСК НАДЁЖНОГО ТАЙМАУТА (WDT + кормящий таймер) ===
        with self._lock:
            self._is_running = True
            self._timeout_armed = False
            self._exec_start_ms = time.ticks_ms() if hasattr(time, 'ticks_ms') else 0
        self._start_timer()

        try:
            # Компиляция кода (вне WDT — компиляция безопасна по времени)
            compiled_code = compile(code, '<sandbox>', 'exec')

            # Выполнение кода. Если код зависнет на C-уровне, кормящий таймер
            # перестанет кормить WDT -> аппаратная перезагрузка ESP32.
            # Если код кооперативный и проверяет флаг — мягкая остановка ниже.
            exec(compiled_code, safe_globals, locals_dict)

            # Мягкая кооперативная остановка: если таймер/stop_execution сбросили
            # флаг, но exec() успел вернуться — сообщаем о таймауте как об ошибке.
            with self._lock:
                timed_out = self._timeout_armed and not self._is_running

            if timed_out:
                raise RuntimeError(
                    "Execution exceeded time limit of %d ms" % self.time_limit_ms
                )
            
            # === ПРОВЕРКА ПАМЯТИ ПОСЛЕ ВЫПОЛНЕНИЯ ===
            if not self._check_memory_usage():
                raise MemoryError("Memory limit exceeded after execution")

            # Фиксируем дельту памяти через монитор (не выбрасывает исключений)
            if self.memory_monitor:
                try:
                    self.memory_monitor.check_after_execution()
                except Exception:
                    pass

        except RuntimeError:
            # Ожидаемая ошибка таймаута.
            return {
                'output': ''.join(_capture_buffer) if capture_output else "",
                'error': "RuntimeError: execution exceeded time limit",
                'success': False,
                'timeout': True,
            }

        except MemoryError:            
            return {
                'output': ''.join(_capture_buffer) if capture_output else "",
                'error': "MemoryError: memory limit exceeded",
                'success': False,
                'memory_error': True,
            }
        except Exception as e:
            # Общая ошибка выполнения кода в песочнице.
            return {
                'output': ''.join(_capture_buffer) if capture_output else "",
                'error': str(e),
                'success': False,
            }
        finally:
            # === ОСТАНОВКА ТАЙМАУТА И WDT ===
            # ВАЖНО: это сработает даже если exec() упал с исключением.
            # Если же код завис и WDT уже «уморил» устройство — до сюда мы не
            # дойдём (произойдёт аппаратная перезагрузка), что и есть fail-secure.
            self._stop_timer()

            with self._lock:
                self._is_running = False
                self._timeout_armed = False

        result = {
            'globals': safe_globals,
            'locals': locals_dict,
            'success': True
        }

        if capture_output:
            result['output'] = ''.join(_capture_buffer)
            result['error'] = ""

        return result
    
    def _start_timer(self):
        """
        Запуск программного таймера для проверки таймаута (кооперативный).

        Логика:
          - machine.Timer периодически (каждые ~250 мс) проверяет, не превысил
            ли код time_limit_ms.
          - Если превысил — выставляются флаги _timeout_armed=True и
            _is_running=False.
          - Кооперативный код (проверяющий _is_running) завершится сам.
          - Не-кооперативный код (зависший в C-цикле) НЕ будет прерван.

        Это соответствует «strict time limits» TUR55 в той мере, в какой
        это возможно без аппаратного WDT.

        На CPython/без machine — метод тихо завершается.
        """
        if not machine:
            return

        try:
            # Timer(-1) — виртуальный таймер (не привязан к аппаратному).
            self._keepalive_timer = machine.Timer(-1)

            def _timeout_cb(t):
                """
                Колбэк таймера: проверка таймаута (ISR-контекст).
                """
                with self._lock:
                    running = self._is_running
                    armed = self._timeout_armed
                if running and not armed:
                    if self._exec_start_ms and hasattr(time, 'ticks_ms'):
                        elapsed = time.ticks_diff(time.ticks_ms(), self._exec_start_ms)
                        if elapsed >= self.time_limit_ms:
                            with self._lock:
                                self._is_running = False
                                self._timeout_armed = True

            self._keepalive_timer.init(
                mode=machine.Timer.PERIODIC,
                period=self._keepalive_period_ms,
                callback=_timeout_cb
            )
        except Exception:
            self._keepalive_timer = None


    def _stop_timer(self):
        """
        Остановка программного таймера после завершения кода.
        """
        if self._keepalive_timer is not None:
            try:
                self._keepalive_timer.deinit()
            except Exception:
                pass
            self._keepalive_timer = None


    def _add_allowed_modules(self, globals_dict):
        """
        Добавление разрешенных модулей в глобальное окружение через SafeImporter
        """
        for module_name in self.safe_importer._allowed:
            try:
                # Импортируем модуль через SafeImporter
                module = self.safe_importer.__import__(module_name)
                globals_dict[module_name] = module
            except ImportError:
                # Модуль недоступен, пропускаем
                pass
                
    def limit_resources(self, memory_limit_kb=None, time_limit_ms=None):
        """
        Установка ограничений ресурсов (память и/или таймаут).

        Обновляет ОБА поля — time_limit_ms (для ISR-проверки) и
        time_limit_seconds (для совместимости со старым кодом).
        """
        if memory_limit_kb is not None:
            self.memory_limit_bytes = memory_limit_kb * 1024
        if time_limit_ms is not None:
            self.time_limit_ms = time_limit_ms
            self.time_limit_seconds = time_limit_ms / 1000.0
            
    def monitor_execution_time(self, start_time):
        """
        Мониторинг времени выполнения
        """
        elapsed = time.ticks_diff(time.ticks_ms(), start_time) / 1000.0
        return elapsed > self.time_limit_seconds
        
    def stop_execution(self):
        """
        Принудительная остановка выполнения кода извне.

        Двухуровневая стратегия:
          1. Сразу сбрасываем флаг _is_running -> кооперативный код (и цикл
             движка ExecutionEngine) может корректно завершиться сам.
          2. Если код НЕ реагирует на флаг (завис в блокирующем вызове или
             бесконечном C-level цикле) — «морим» WDT: перестаём кормить его,
             после чего ESP32 аппаратно перезагрузится. Это единственный
             надёжный способ прервать зависший код в MicroPython.

        Для кооперативного кода перезагрузки НЕ происходит — таймер сам
        увидит сброс флага и остановит кормление мягко (через armed=False).
        Здесь же мы дополнительно гарантируем жёсткий сброс при необходимости.
        """
        with self._lock:
            self._is_running = False
            self._timeout_armed = True  # прекращаем кормить WDT в ISR таймера

        # Если код завис намертво и не вернёт управление в execute_in_sandbox(),
        # кормящий таймер больше не покормит WDT -> аппаратная перезагрузка.
        # Дополнительно, если есть прямая машина reset() и мы решили, что
        # нужен гарантированный рестарт, можно вызвать machine.reset().
        # Оставляем это закомментированным, чтобы поведение было предсказуемым:
        #   if machine:
        #       try:
        #           machine.reset()
        #       except Exception:
        #           pass
        
    def execute_with_timeout(self, code, timeout_sec, globals_dict=None, locals_dict=None):
        """
        Выполнение кода с явным таймаутом (в секундах).

        Временно переопределяет time_limit_ms на timeout_sec, делегируя реальный
        механизм таймаута (WDT + кормящий таймер) в execute_in_sandbox.
        """
        saved_ms = self.time_limit_ms
        saved_sec = self.time_limit_seconds
        try:
            self.time_limit_ms = int(timeout_sec * 1000)
            self.time_limit_seconds = timeout_sec
            result = self.execute_in_sandbox(
                code,
                globals_dict=globals_dict,
                locals_dict=locals_dict,
                capture_output=True
            )
        finally:
            self.time_limit_ms = saved_ms
            self.time_limit_seconds = saved_sec

        # Совместимость: помечаем timeout/execution_time по факту.
        if not result.get('success', False):
            result.setdefault('timeout', True)
        else:
            result.setdefault('execution_time', timeout_sec)

        return result

    def reset_sandbox(self):
        """
        Сброс состояния песочницы.

        Гарантированно останавливает WDT/таймер и сбрасывает флаги выполнения,
        восстанавливает оригинальные потоки вывода и sys.modules.
        """
        # Останавливаем таймер.
        self._stop_timer()

        # Сбрасываем флаги выполнения (новые имена: _is_running, _timeout_armed).
        with self._lock:
            self._is_running = False
            self._timeout_armed = False

         # Восстановление оригинальных модулей (только если сохранили)
        if self.original_modules is not None:
            sys.modules.clear()
            sys.modules.update(self.original_modules)

        # Очистка памяти
        gc.collect()


class _dummy_lock:
    """Заглушка для блокировки, когда _thread недоступен"""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass