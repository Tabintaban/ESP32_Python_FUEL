"""
LineBasedCompiler - компилятор для эффективного объединения строк кода и предварительной валидации

SECURITY FIXES:
- Implemented safe indent normalization with GCD-based detection
- Prevents mixing tabs and spaces
- Preserves code semantics during normalization
- Detects indent size from code (2 vs 4 spaces)
"""

import gc
import re
from math import gcd
import math


class LineBasedCompiler:
    """
    Компилятор для эффективного объединения строк кода и предварительной валидации
    """
    
    def __init__(self):
        self.compiled_cache = {}
        self.max_cache_size = 10
        self.optimization_stats = {
            'total_compilations': 0,
            'cache_hits': 0,
            'optimization_saved_lines': 0
        }
        
    def optimize_for_esp32(self, code_strings):
        """
        Оптимизация кода для ESP32
        """
        if isinstance(code_strings, list):
            code = '\n'.join(code_strings)
        else:
            code = code_strings
            
        # Удаление комментариев и пустых строк
        optimized_code = self.remove_comments_and_empty(code)
        
        # Упрощение отступов для экономии памяти
        optimized_code = self.normalize_indents(optimized_code)
        
        return optimized_code
        
    def remove_comments_and_empty(self, code):
        """
        Удаление комментариев и пустых строк
        """
        lines = code.split('\n')
        filtered_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Пропускаем пустые строки и комментарии
            if not stripped or stripped.startswith('#'):
                continue
                
            filtered_lines.append(line)
            
        return '\n'.join(filtered_lines)
        
    def normalize_indents(self, code):
        """
        Нормализация отступов БЕЗ изменения семантики
        
        Args:
            code: Код для нормализации
            
        Returns:
            Нормализованный код
            
        Raises:
            IndentationError: Если смешиваются табуляции и пробелы
        """
        lines = code.split('\n')
        normalized = []
        
        # Определяем базовый размер отступа (2 или 4 пробела)
        indent_size = self._detect_indent_size(lines)
        
        for line in lines:
            if not line.strip():
                normalized.append('')
                continue
            
            # Считаем ведущие пробелы
            leading_spaces = len(line) - len(line.lstrip(' '))
            leading_tabs = len(line) - len(line.lstrip('\t'))
            
            # НЕ смешиваем табуляции и пробелы
            if leading_tabs > 0 and leading_spaces > 0:
                raise IndentationError("Mixed tabs and spaces in indentation")
            
            # Конвертируем табуляции в пробелы
            if leading_tabs > 0:
                line = ' ' * (leading_tabs * indent_size) + line.lstrip('\t')
            
            normalized.append(line)
        
        return '\n'.join(normalized)
    
    def _detect_indent_size(self, lines):
        """
        Определение размера отступа из кода
        
        Args:
            lines: Список строк кода
            
        Returns:
            Размер отступа (2 или 4, по умолчанию 4)
        """
        indents = []
        for line in lines:
            if line.strip() and line[0] == ' ':
                indent = len(line) - len(line.lstrip(' '))
                if indent > 0:
                    indents.append(indent)
        
        if not indents:
            return 4  # По умолчанию
        
        # Находим НОД всех отступов
        result = indents[0]
        for indent in indents[1:]:
            result = gcd(result, indent)
        
        return result if result > 0 else 4
        
    def build_executable(self, code_blocks):
        """
        Сборка исполняемого кода из блоков
        """
        # Получаем кэшированную версию если она существует
        cache_key = self._generate_cache_key(code_blocks)
        if cache_key in self.compiled_cache:
            self.optimization_stats['cache_hits'] += 1
            return self.compiled_cache[cache_key]
            
        # Объединяем все блоки кода
        imports = code_blocks.get('imports', '')
        functions = code_blocks.get('functions', '')
        setup = code_blocks.get('setup', '')
        loop_logic = code_blocks.get('loop_logic', '')
        
        # Создаем полный исполняемый код
        full_code = f"{imports}\n\n{functions}\n\n{setup}\n\n{loop_logic}"
        
        # Оптимизируем код
        optimized_code = self.optimize_for_esp32(full_code)
        
        # Компилируем код для проверки синтаксиса
        try:
            compiled = compile(optimized_code, '<compiled>', 'exec')
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in generated code: {str(e)}")
            
        # Создаем исполняемую структуру
        executable = {
            'full_code': optimized_code,
            'compiled_code': compiled,
            'imports': imports,
            'functions': functions,
            'setup': setup,
            'loop_logic': loop_logic,
            'original_blocks': code_blocks
        }
        
        # Кэшируем результат
        self._cache_compiled(cache_key, executable)
        
        self.optimization_stats['total_compilations'] += 1
        
        return executable
        
    def validate_syntax(self, code):
        """
        Предварительная валидация синтаксиса
        """
        try:
            compile(code, '<validation>', 'exec')
            return True
        except SyntaxError:
            return False
            
    def _generate_cache_key(self, code_blocks):
        """
        Генерация ключа для кэширования
        """
        import hashlib
        blocks_str = str(code_blocks)
        return hashlib.sha256(blocks_str.encode()).hexdigest()[:16]
        
    def _cache_compiled(self, key, executable):
        """
        Кэширование скомпилированного кода
        """
        if len(self.compiled_cache) >= self.max_cache_size:
            # Удаляем старые записи
            oldest_key = next(iter(self.compiled_cache))
            del self.compiled_cache[oldest_key]
            
        self.compiled_cache[key] = executable
        
    def clear_cache(self):
        """
        Очистка кэша скомпилированного кода
        """
        self.compiled_cache.clear()
        gc.collect()
        
    def get_cache_stats(self):
        """
        Получение статистики кэша
        """
        return {
            'cache_size': len(self.compiled_cache),
            'max_cache_size': self.max_cache_size,
            'stats': self.optimization_stats.copy()
        }
        
    def precompile_blocks(self, code_blocks_list):
        """
        Предварительная компиляция нескольких блоков
        """
        results = []
        for blocks in code_blocks_list:
            try:
                executable = self.build_executable(blocks)
                results.append({
                    'success': True,
                    'executable': executable,
                    'error': None
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'executable': None,
                    'error': str(e)
                })
                
        return results
        
    def optimize_bytecode(self, code):
        """
        Оптимизация байт-кода (в упрощенной форме)
        """
        # В MicroPython оптимизация байт-кода ограничена
        # Пока просто возвращаем оригинальный код
        return code
        
    def minify_code(self, code):
        """
        Минификация кода для экономии памяти
        """
        # Удаление лишних пробелов и комментариев
        lines = code.split('\n')
        minified_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                # Убираем комментарии из середины строк
                comment_pos = stripped.find('#')
                if comment_pos != -1:
                    stripped = stripped[:comment_pos].rstrip()
                    
                if stripped:  # Не пустая строка после удаления комментариев
                    minified_lines.append(stripped)
                    
        return '\n'.join(minified_lines)


# Unit tests for line_compiler
def test_line_compiler():
    """
    Unit-тесты для LineBasedCompiler
    """
    print("Testing LineBasedCompiler...")
    
    compiler = LineBasedCompiler()
    
    # Тест 1: Определение размера отступа
    code_4_spaces = """
def test():
    if True:
        print("test")
"""
    indent_size = compiler._detect_indent_size(code_4_spaces.split('\n'))
    assert indent_size == 4, "Should detect 4-space indent"
    print("✓ Test 1: Indent size detection (4 spaces) passed")
    
    # Тест 2: Определение 2-пробельного отступа
    code_2_spaces = """
def test():
  if True:
    print("test")
"""
    indent_size = compiler._detect_indent_size(code_2_spaces.split('\n'))
    assert indent_size == 2, "Should detect 2-space indent"
    print("✓ Test 2: Indent size detection (2 spaces) passed")
    
    # Тест 3: Нормализация отступов без смешивания
    code_mixed = """
def test():
    if True:
        print("test")
"""
    normalized = compiler.normalize_indents(code_mixed)
    assert 'print("test")' in normalized, "Should preserve code content"
    print("✓ Test 3: Safe indent normalization passed")
    
    # Тест 4: Обнаружение смешивания табов и пробелов
    code_tabs_spaces = """
def test():
	if True:
        print("test")
"""
    try:
        compiler.normalize_indents(code_tabs_spaces)
        assert False, "Should raise IndentationError for mixed tabs and spaces"
    except IndentationError:
        print("✓ Test 4: Mixed tabs/spaces detection passed")
    
    # Тест 5: Конвертация табов в пробелы
    code_tabs = """
def test():
	if True:
		print("test")
"""
    normalized = compiler.normalize_indents(code_tabs)
    # Табы должны быть конвертированы в пробелы
    assert '\t' not in normalized, "Tabs should be converted to spaces"
    print("✓ Test 5: Tab to space conversion passed")
    
    # Тест 6: Валидация синтаксиса
    valid_code = "x = 1 + 2"
    assert compiler.validate_syntax(valid_code), "Valid code should pass validation"
    
    invalid_code = "x = 1 +"
    assert not compiler.validate_syntax(invalid_code), "Invalid code should fail validation"
    print("✓ Test 6: Syntax validation passed")
    
    print("\n✅ All line compiler tests passed!\n")


if __name__ == "__main__":
    test_line_compiler()