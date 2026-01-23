"""
MemoryOptimizer - класс для управления памятью и оптимизации потребления ресурсов
"""

import gc
import sys


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
        """
        gc.collect()  # Собираем мусор для актуальных данных
        
        stats = {
            'max_allowed_bytes': self.max_memory_bytes,
            'buffer_memory_used': sum(self.buffer_sizes.values()),
            'buffers_count': len(self.buffers),
            'log_entries_count': len(self.memory_log),
            'monitoring_enabled': self.monitoring_enabled
        }
        
        return stats
        
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


# Пример использования:
if __name__ == "__main__":
    optimizer = MemoryOptimizer(max_memory_kb=25)
    
    # Предварительное выделение буферов
    buffers_config = {
        'input_buffer': 1024,
        'output_buffer': 1024,
        'temp_buffer': 512
    }
    
    buffers = optimizer.preallocate_buffers(buffers_config)
    print(f"Allocated buffers: {list(buffers.keys())}")
    
    # Мониторинг памяти
    mem_stats = optimizer.monitor_memory_usage()
    print(f"Memory stats: {mem_stats}")
    
    # Проверка давления на память
    pressure = optimizer.check_memory_pressure()
    print(f"Memory pressure: {pressure}")
    
    # Оптимизация bytearray
    test_data = ["hello", "world", ["nested", "list"]]
    optimized_data = optimizer.optimize_bytearray_usage(test_data)
    print(f"Original types: {[type(x) for x in test_data]}")
    print(f"Optimized types: {[type(x) for x in optimized_data if not isinstance(x, list)]}")
    
    # Статистика памяти
    final_stats = optimizer.get_memory_stats()
    print(f"Final stats: {final_stats}")