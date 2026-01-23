"""
LineBasedCompiler - компилятор для эффективного объединения строк кода и предварительной валидации
"""

import gc
import re


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
        Нормализация отступов (используем табуляцию вместо пробелов где возможно)
        """
        lines = code.split('\n')
        normalized_lines = []
        
        for line in lines:
            if line.strip():  # Не пустая строка
                # Заменяем 4 пробела на табуляцию
                line = re.sub(r'^(\s*)', lambda m: m.group(1).replace('    ', '\t'), line)
            normalized_lines.append(line)
            
        return '\n'.join(normalized_lines)
        
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


# Пример использования:
if __name__ == "__main__":
    compiler = LineBasedCompiler()
    
    # Пример блоков кода
    code_blocks = {
        'imports': 'import machine\nimport time',
        'functions': 'def blink(pin):\n    pin.value(1)\n    time.sleep(0.5)\n    pin.value(0)',
        'setup': 'led = machine.Pin(2, machine.Pin.OUT)',
        'loop_logic': 'blink(led)\ntime.sleep(1)'
    }
    
    print("Building executable...")
    executable = compiler.build_executable(code_blocks)
    
    print("Executable keys:", list(executable.keys()))
    print("Full code length:", len(executable['full_code']))
    print("Cache stats:", compiler.get_cache_stats())
    
    # Тестируем оптимизацию
    test_code = """
# This is a comment
def test():
    x = 1    # inline comment
    y = 2
    return x + y
    
# Another comment

z = test()
"""
    
    print("\nOriginal code length:", len(test_code))
    optimized = compiler.optimize_for_esp32(test_code)
    print("Optimized code length:", len(optimized))
    minified = compiler.minify_code(test_code)
    print("Minified code length:", len(minified))