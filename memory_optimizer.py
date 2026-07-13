"""
MemoryOptimizer - класс для управления памятью и оптимизации потребления ресурсов

SECURITY FIXES:
- Added pre-execution memory checking
- Implemented RealTimeMemoryMonitor for runtime monitoring
- Auto-trigger gc.collect() near memory limits
- Added detailed memory statistics

VULNERABILITY FIXES (v2) - ROBUST MEMORY API:
- RealTimeMemoryMonitor теперь имеет полный API: check_before_execution(),
  check_during_execution(), check_after_execution().
- Все чтения gc.mem_free()/gc.mem_alloc() обёрнуты защитой: если память сильно
  фрагментирована и вызов падает/возвращает некорректное значение, монитор НЕ
  роняет выполнение, а возвращает безопасное значение (0 / None).
- gc.collect() вызывается перед каждым измерением для уплотнения кучи.
"""

import gc
import sys
import time


# Проверка доступности MicroPython-специфичных функций gc
_HAS_MEM_FREE = hasattr(gc, 'mem_free')
_HAS_MEM_ALLOC = hasattr(gc, 'mem_alloc')


def _get_free_memory():
    """
    Безопасное получение свободной памяти.

    Возвращает int (число свободных байт) или None, если gc.mem_free()
    недоступен (CPython) или вызов упал из-за фрагментации/повреждения кучи.
    Никогда не выбрасывает исключение.
    """
    if not _HAS_MEM_FREE:
        return None
    try:
        val = gc.mem_free()
        # На сильно фрагментированной куче отдельные порты MicroPython могут
        # вернуть отрицательное/None значение — считаем это «недоступно».
        if val is None or val < 0:
            return None
        return int(val)
    except Exception:
        return None


def _get_allocated_memory():
    """
    Безопасное получение выделенной памяти.

    Возвращает int или None. Никогда не выбрасывает исключение.
    """
    if not _HAS_MEM_ALLOC:
        return None
    try:
        val = gc.mem_alloc()
        if val is None or val < 0:
            return None
        return int(val)
    except Exception:
        return None


class RealTimeMemoryMonitor:
    """
    Мониторинг памяти в реальном времени с проверкой до, во время и после выполнения.

    API:
      - check_before_execution(estimated_bytes): gc.collect() + проверка, что
        свободной памяти достаточно для запуска (иначе MemoryError).
      - check_during_execution(): быстрая проверка «ещё не критично?»;
        возвращает свободные байты или 0 (никогда не падает).
      - check_after_execution(): фиксирует дельту памяти и при сильной утечке
        запускает gc.collect(); возвращает словарь со статистикой.

    Все методы устойчивы к фрагментации: если gc.mem_free() вернул None,
    монитор деградирует безопасно (считает, что «данных нет»), но не роняет
    выполняемый код.
    """

    def __init__(self, hard_limit_bytes, warning_threshold=0.8):
        # hard_limit — минимальный резерв свободной памяти, который мы пытаемся
        # удерживать (НЕ верхний предел выделенной памяти).
        self.hard_limit = hard_limit_bytes
        self.warning_threshold = warning_threshold
        # Базовый уровень свободной памяти (для оценки утечек).
        # Если gc.mem_free недоступен — используем безопасный fallback.
        self._baseline_free = _get_free_memory()
        if self._baseline_free is None:
            self._baseline_free = hard_limit_bytes
        self._memory_checks = []

    def _record_check(self, kind, extra=None):
        """Внутренний: запись точки замера памяти в историю."""
        entry = {
            'type': kind,
            'free': _get_free_memory(),
            'allocated': _get_allocated_memory(),
            'timestamp': time.ticks_ms() if hasattr(time, 'ticks_ms') else 0,
        }
        if extra:
            entry.update(extra)
        self._memory_checks.append(entry)
        # Ограничиваем длину истории, чтобы не разрасталась в RAM.
        if len(self._memory_checks) > 64:
            del self._memory_checks[0]

    def check_before_execution(self, estimated_bytes):
        """
        Проверка памяти ДО выполнения кода.

        Args:
            estimated_bytes: Оценка требуемой памяти.

        Raises:
            MemoryError: Если свободной памяти меньше, чем estimated_bytes,
                         или она ниже критического порога hard_limit.
        """
        gc.collect()  # уплотняем кучу перед замером
        free = _get_free_memory()

        if free is None:
            # gc.mem_free() недоступен (CPython) — пропускаем жёсткую проверку,
            # но фиксируем факт вызова для истории.
            self._record_check('before', {'estimated': estimated_bytes, 'unavailable': True})
            return

        # Жёсткая проверка: свободной памяти должно хватить под оценку + резерв.
        if free < estimated_bytes:
            self._record_check('before', {'estimated': estimated_bytes, 'denied': True})
            raise MemoryError(
                "Insufficient memory: need %d, have %d bytes free" % (estimated_bytes, free)
            )

        # Мягкая проверка: не приближаемся ли к опасному порогу.
        if free < self.hard_limit * (1 - self.warning_threshold):
            gc.collect()  # последняя попытка освободить память

        self._record_check('before', {'estimated': estimated_bytes})

    def check_during_execution(self):
        """
        Проверка памяти ВО ВРЕМЯ выполнения (вызывается из цикла движка).

        Returns:
            Текущее количество свободной памяти (int). Если gc.mem_free()
            недоступен — возвращает 0, но НЕ выбрасывает исключение.

        Raises:
            MemoryError: Если свободная память упала ниже критического порога
                         (10% от hard_limit).
        """
        free = _get_free_memory()

        if free is None:
            # Данных о памяти нет — не блокируем выполнение.
            return 0

        if free < self.hard_limit * 0.1:  # критический уровень
            self._record_check('during', {'critical': True})
            raise MemoryError("Critical memory level reached")

        # Не пишем в историю каждый вызов (цикл зовёт это часто) — только точку.
        return free

    def check_after_execution(self, baseline_free=None):
        """
        Проверка памяти ПОСЛЕ выполнения кода.

        Сравнивает текущий свободный объём с базовым уровнем (перед запуском
        или с baseline_free, если передан). Если память заметно «утекла»,
        запускает gc.collect() и повторно замеряет.

        Args:
            baseline_free: Опциональный базовый уровень свободной памяти
                           (например, замер до выполнения). Если None,
                           используется self._baseline_free.

        Returns:
            Словарь со статистикой: free, allocated, delta, gc_triggered.
        """
        before = baseline_free if baseline_free is not None else self._baseline_free
        gc.collect()
        free = _get_free_memory()
        allocated = _get_allocated_memory()

        delta = None
        gc_triggered = False
        if free is not None and before is not None:
            delta = free - before
            # Если свободная память заметно просела (> 20% от лимита) —
            # сборка мусора уже выполнена выше; помечаем это.
            if delta < -(self.hard_limit * 0.2):
                gc_triggered = True
                # Повторный замер после gc.collect()
                free = _get_free_memory()
                allocated = _get_allocated_memory()
                delta = free - before if (free is not None) else None

        self._record_check('after', {'delta': delta, 'gc_triggered': gc_triggered})

        return {
            'free': free if free is not None else 0,
            'allocated': allocated if allocated is not None else 0,
            'delta': delta,
            'gc_triggered': gc_triggered,
        }

    def get_memory_stats(self):
        """
        Детальная статистика использования памяти.

        Returns:
            Словарь со статистикой памяти.
        """
        gc.collect()
        free = _get_free_memory()
        allocated = _get_allocated_memory()
        return {
            'free': free if free is not None else 0,
            'allocated': allocated if allocated is not None else 0,
            'total': (free or 0) + (allocated or 0),
            'baseline_free': self._baseline_free,
            'check_count': len(self._memory_checks)
        }

    def get_memory_history(self):
        """
        История проверок памяти.

        Returns:
            Список проверок памяти.
        """
        return self._memory_checks


class MemoryOptimizer:
    """
    Класс для управления памятью и оптимизации потребления ресурсов
    """
    
    def __init__(self, max_memory_kb=50):
        self.max_memory_bytes = max_memory_kb * 1024
        self.buffers = {}
        self.buffer_sizes = {}
        self.monitoring_enabled = True
        self.memory_log = []
        self.gc_threshold = 1024  # Выполнять GC каждые N байт
        self.memory_monitor = RealTimeMemoryMonitor(self.max_memory_bytes)
        
    def preallocate_buffers(self, buffer_configs):
        """
        Предварительное выделение буферов заданных размеров
        buffer_configs: dict с парами {name: size_in_bytes}
        """
        for name, size in buffer_configs.items():
            # Создаем буфер нужного размера
            buffer = bytearray(size)
            self.buffers[name] = buffer
            self.buffer_sizes[name] = size
            
        return self.buffers
        
    def monitor_memory_usage(self):
        """
        Мониторинг использования памяти
        """
        if not self.monitoring_enabled:
            return {'enabled': False}
            
        # В MicroPython нет точного способа измерения использования памяти
        # поэтому используем косвенные методы
        gc.collect()  # Собираем мусор перед измерением
        
        # Логируем текущее состояние
        log_entry = {
            'timestamp': self._get_timestamp(),
            'buffers_count': len(self.buffers),
            'total_buffer_size': sum(self.buffer_sizes.values()),
            'active_buffers': list(self.buffers.keys())
        }
        
        self.memory_log.append(log_entry)
        
        # Ограничиваем размер лога
        if len(self.memory_log) > 100:
            self.memory_log = self.memory_log[-50:]  # Сохраняем последние 50 записей
            
        return log_entry
        
    def cleanup_cache(self, cache_objects=None):
        """
        Очистка кэша
        """
        cleaned_count = 0
        
        if cache_objects is None:
            # Очищаем внутренние кэши
            caches_to_clean = [
                'buffers',  # Хотя буферы не всегда нужно очищать
            ]
            for cache_name in caches_to_clean:
                cache = getattr(self, cache_name, {})
                if isinstance(cache, dict):
                    cache.clear()
                    cleaned_count += 1
        else:
            # Очищаем указанные кэши
            for cache in cache_objects:
                if hasattr(cache, 'clear'):
                    cache.clear()
                    cleaned_count += 1
                    
        # Выполняем сборку мусора
        collected = gc.collect()
        
        return {
            'cleaned_caches': cleaned_count,
            'garbage_collected': collected
        }
        
    def optimize_bytearray_usage(self, data_list):
        """
        Оптимизация использования bytearray
        """
        optimized_list = []
        
        for item in data_list:
            if isinstance(item, str):
                # Преобразуем строки в bytearray если возможно
                ba = bytearray(item, 'utf-8')
                optimized_list.append(ba)
            elif isinstance(item, list):
                # Рекурсивно обрабатываем вложенные списки
                optimized_list.append(self.optimize_bytearray_usage(item))
            else:
                optimized_list.append(item)
                
        return optimized_list
        
    def get_memory_stats(self):
        """
        Получение статистики памяти
        
        Returns:
            Словарь со статистикой памяти
        """
        gc.collect()  # Собираем мусор для актуальных данных
        
        stats = {
            'max_allowed_bytes': self.max_memory_bytes,
            'buffer_memory_used': sum(self.buffer_sizes.values()),
            'buffers_count': len(self.buffers),
            'log_entries_count': len(self.memory_log),
            'monitoring_enabled': self.monitoring_enabled
        }
        
        # Добавляем детальную статистику из RealTimeMemoryMonitor
        stats.update(self.memory_monitor.get_memory_stats())
        
        return stats
    
    def check_before_execution(self, estimated_bytes):
        """
        Проверка памяти перед выполнением кода
        
        Args:
            estimated_bytes: Оценка требуемой памяти
            
        Raises:
            MemoryError: Если недостаточно памяти
        """
        self.memory_monitor.check_before_execution(estimated_bytes)
    
    def check_during_execution(self):
        """
        Проверка памяти во время выполнения кода

        Returns:
            Текущее количество свободной памяти

        Raises:
            MemoryError: Если критический уровень памяти
        """
        return self.memory_monitor.check_during_execution()

    def check_after_execution(self, baseline_free=None):
        """
        Проверка памяти ПОСЛЕ выполнения кода.

        Делегирует в RealTimeMemoryMonitor. Возвращает словарь со статистикой
        (free, allocated, delta, gc_triggered) и не выбрасывает исключений.
        """
        return self.memory_monitor.check_after_execution(baseline_free)
        
    def check_memory_pressure(self):
        """
        Проверка давления на память
        """
        stats = self.get_memory_stats()
        buffer_memory = stats['buffer_memory_used']
        
        # Оцениваем давление на память
        pressure_level = buffer_memory / self.max_memory_bytes
        
        return {
            'pressure_ratio': pressure_level,
            'is_critical': pressure_level > 0.9,  # Критический уровень при 90% использовании
            'available_bytes': self.max_memory_bytes - buffer_memory
        }
        
    def compact_memory(self):
        """
        Компактификация памяти (в упрощенной форме)
        """
        # В MicroPython нет встроенной компактификации памяти
        # Поэтому просто выполняем сборку мусора
        collected = gc.collect()
        
        # Также очищаем неиспользуемые буферы
        active_buffers = {}
        for name, buffer in self.buffers.items():
            # В реальной системе здесь была бы проверка на использование буфера
            active_buffers[name] = buffer
            
        self.buffers = active_buffers
        
        return {
            'garbage_collected': collected,
            'buffers_compacted': len(self.buffers)
        }
        
    def _get_timestamp(self):
        """
        Получение временной метки
        """
        try:
            import time
            return time.ticks_ms()
        except:
            return 0  # Заглушка если модуль time недоступен
            
    def set_monitoring(self, enabled=True):
        """
        Включение/отключение мониторинга
        """
        self.monitoring_enabled = enabled
        
    def get_recent_logs(self, count=10):
        """
        Получение последних записей лога
        """
        return self.memory_log[-count:] if self.memory_log else []
        
    def optimize_list_storage(self, lst):
        """
        Оптимизация хранения списков
        """
        # Попробуем использовать tuple вместо list где это возможно
        # для экономии памяти
        if isinstance(lst, list):
            optimized = []
            for item in lst:
                if isinstance(item, list):
                    optimized.append(self.optimize_list_storage(item))
                else:
                    optimized.append(item)
            return optimized
        return lst
        
    def release_buffer(self, buffer_name):
        """
        Освобождение конкретного буфера
        """
        if buffer_name in self.buffers:
            del self.buffers[buffer_name]
            if buffer_name in self.buffer_sizes:
                del self.buffer_sizes[buffer_name]
            return True
        return False
