"""
FastJSONLoader - оптимизированный парсер JSON для быстрой загрузки данных
"""

import json
import gc
from crypto_manager import CryptoManager


class FastJSONLoader:
    """
    Оптимизированный парсер JSON для быстрой загрузки данных
    """
    
    def __init__(self):
        self.crypto_manager = CryptoManager()
        self.cache = {}
        self.max_cache_size = 5  # Максимальный размер кэша
        
    def load_encrypted(self, filepath, key):
        """
        Загрузка зашифрованного JSON-файла
        """
        # Проверяем кэш
        cache_key = f"{filepath}_{hash(key)}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            # Читаем файл
            with open(filepath, 'r') as f:
                encrypted_data = f.read()
                
            # Дешифруем
            decrypted_data = self.crypto_manager.decrypt_data(encrypted_data, key)
            
            # Парсим JSON
            parsed_data = self._parse_json_optimized(decrypted_data)
            
            # Кэшируем
            self._cache_result(cache_key, parsed_data)
            
            return parsed_data
            
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {filepath}")
        except Exception as e:
            raise e
            
    def _parse_json_optimized(self, json_str):
        """
        Оптимизированный парсер JSON
        """
        # В MicroPython используем стандартный json.loads
        # Но с дополнительной оптимизацией
        return json.loads(json_str)
        
    def extract_code_lines(self, json_data):
        """
        Извлечение строк кода из JSON-данных
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
            
        code_blocks = {
            'imports': '\n'.join(json_data.get('imports', [])),
            'functions': '\n'.join(json_data.get('functions', [])),
            'setup': '\n'.join(json_data.get('setup', [])),
            'loop_logic': '\n'.join(json_data.get('loop_logic', []))
        }
        
        return code_blocks
        
    def streaming_parse(self, filepath):
        """
        Поточное чтение файла (в упрощенной форме для MicroPython)
        """
        # В MicroPython нет полноценного поточного парсинга JSON
        # Поэтому читаем весь файл сразу
        with open(filepath, 'r') as f:
            content = f.read()
            
        return content
        
    def _cache_result(self, key, result):
        """
        Кэширование результата
        """
        if len(self.cache) >= self.max_cache_size:
            # Удаляем старые записи
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            
        self.cache[key] = result
        
    def clear_cache(self):
        """
        Очистка кэша
        """
        self.cache.clear()
        gc.collect()
        
    def get_cached_keys(self):
        """
        Получение списка закэшированных ключей
        """
        return list(self.cache.keys())
        
    def load_json_optimized(self, filepath):
        """
        Загрузка JSON-файла с оптимизацией
        """
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                
            return json.loads(content)
            
        except Exception as e:
            raise e
            
    def extract_section(self, json_data, section_name):
        """
        Извлечение конкретной секции из JSON-данных
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
            
        return json_data.get(section_name, [])
        
    def combine_code_sections(self, json_data):
        """
        Объединение всех секций кода в один блок
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
            
        imports = '\n'.join(json_data.get('imports', []))
        functions = '\n'.join(json_data.get('functions', []))
        setup = '\n'.join(json_data.get('setup', []))
        loop_logic = '\n'.join(json_data.get('loop_logic', []))
        
        combined = {
            'imports': imports,
            'functions': functions,
            'setup': setup,
            'loop_logic': loop_logic,
            'full_code': f"{imports}\n\n{functions}\n\n{setup}\n\n{loop_logic}"
        }
        
        return combined


# Пример использования:
if __name__ == "__main__":
    loader = FastJSONLoader()
    
    # Пример данных для тестирования
    sample_json = {
        "imports": ["import machine", "import time"],
        "functions": ["def blink(pin):", "    pin.value(1)", "    time.sleep(0.5)", "    pin.value(0)"],
        "setup": ["led = machine.Pin(2, machine.Pin.OUT)"],
        "loop_logic": ["blink(led)", "time.sleep(1)"]
    }
    
    print("Combined code sections:")
    combined = loader.combine_code_sections(sample_json)
    for section, code in combined.items():
        print(f"{section}: {len(code)} chars")
        
    print("\nExtracted code blocks:")
    blocks = loader.extract_code_lines(sample_json)
    for block, code in blocks.items():
        print(f"{block}: {len(code)} chars")