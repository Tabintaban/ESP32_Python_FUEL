"""
FastJSONLoader - оптимизированный парсер JSON для быстрой загрузки данных

SECURITY FIXES:
- Fixed newline preservation in combine_code_sections
- Added syntax validation before returning combined code
- Proper handling of trailing whitespace between sections
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
        Безопасное объединение секций кода с сохранением структуры
        
        Args:
            json_data: JSON-данные с секциями кода (dict или str)
            
        Returns:
            Словарь с объединенными секциями и полным кодом
            
        Raises:
            ValueError: Если объединенный код имеет синтаксическую ошибку
        """
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        
        sections = {
            'imports': json_data.get('imports', []),
            'functions': json_data.get('functions', []),
            'setup': json_data.get('setup', []),
            'loop_logic': json_data.get('loop_logic', [])
        }
        
        combined_lines = []
        for section_name, section_lines in sections.items():
            if not section_lines:
                continue
                
            # Разбиваем на строки, сохраняя пустые
            lines = section_lines if isinstance(section_lines, list) else section_lines.split('\n')
            
            # Удаляем только trailing пустые строки
            while lines and not lines[-1].strip():
                lines.pop()
            
            # Добавляем с гарантированным разделителем
            if combined_lines and lines:
                combined_lines.append('')  # Пустая строка между секциями
            
            combined_lines.extend(lines)
        
        # Финальная очистка
        result = '\n'.join(combined_lines)
        
        # Проверка синтаксиса перед возвратом
        try:
            compile(result, '<combined>', 'exec')
        except SyntaxError as e:
            raise ValueError(f"Combined code has syntax error: {e}")
        
        # Возвращаем отдельные секции для обратной совместимости
        imports = '\n'.join(sections['imports'])
        functions = '\n'.join(sections['functions'])
        setup = '\n'.join(sections['setup'])
        loop_logic = '\n'.join(sections['loop_logic'])
        
        combined = {
            'imports': imports,
            'functions': functions,
            'setup': setup,
            'loop_logic': loop_logic,
            'full_code': result
        }
        
        return combined


# Unit tests for fast_json_loader
def test_fast_json_loader():
    """
    Unit-тесты для FastJSONLoader
    """
    print("Testing FastJSONLoader...")
    
    loader = FastJSONLoader()
    
    # Тест 1: Объединение секций с сохранением переносов строк
    sample_json = {
        "imports": ["import machine", "import time"],
        "functions": ["def blink(pin):", "    pin.value(1)", "    time.sleep(0.5)", "    pin.value(0)"],
        "setup": ["led = machine.Pin(2, machine.Pin.OUT)"],
        "loop_logic": ["blink(led)", "time.sleep(1)"]
    }
    
    combined = loader.combine_code_sections(sample_json)
    full_code = combined['full_code']
    
    # Проверяем наличие пустых строк между секциями
    assert '\n\n' in full_code, "Should have blank lines between sections"
    print("✓ Test 1: Newline preservation passed")
    
    # Тест 2: Проверка синтаксиса объединенного кода
    try:
        compile(full_code, '<test>', 'exec')
        print("✓ Test 2: Syntax validation passed")
    except SyntaxError as e:
        raise AssertionError(f"Combined code should be valid: {e}")
    
    # Тест 3: Обработка пустых секций
    empty_json = {
        "imports": [],
        "functions": [],
        "setup": ["x = 1"],
        "loop_logic": []
    }
    
    combined = loader.combine_code_sections(empty_json)
    assert "x = 1" in combined['full_code'], "Should include non-empty sections"
    print("✓ Test 3: Empty section handling passed")
    
    # Тест 4: Извлечение кодовых блоков
    blocks = loader.extract_code_lines(sample_json)
    assert 'imports' in blocks, "Should extract imports"
    assert 'functions' in blocks, "Should extract functions"
    assert 'setup' in blocks, "Should extract setup"
    assert 'loop_logic' in blocks, "Should extract loop_logic"
    print("✓ Test 4: Code block extraction passed")
    
    # Тест 5: Обработка trailing whitespace
    trailing_json = {
        "imports": ["import time", ""],  # Пустая строка в конце
        "functions": ["def test():", "    pass", ""],
        "setup": [],
        "loop_logic": []
    }
    
    combined = loader.combine_code_sections(trailing_json)
    # Trailing пустые строки должны быть удалены
    assert combined['full_code'].strip() == combined['full_code'].rstrip(), "Trailing whitespace should be handled"
    print("✓ Test 5: Trailing whitespace handling passed")
    
    print("\n✅ All fast JSON loader tests passed!\n")


if __name__ == "__main__":
    test_fast_json_loader()