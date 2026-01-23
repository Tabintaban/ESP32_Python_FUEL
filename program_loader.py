"""
ProgramLoader - класс для загрузки и валидации программ из зашифрованных JSON-файлов
"""

import json
import gc
from crypto_manager import CryptoManager
from lightweight_security import LightweightSecurity


class ProgramLoader:
    """
    Класс для загрузки и валидации программ из зашифрованных JSON-файлов
    """
    
    def __init__(self):
        self.crypto_manager = CryptoManager()
        self.security_checker = LightweightSecurity()
        self.loaded_programs = {}
        self.validation_cache = {}
        
    def load_program(self, filepath, key):
        """
        Загрузка программы из файла
        """
        try:
            # Чтение зашифрованного файла
            with open(filepath, 'r') as f:
                encrypted_data = f.read()
                
            # Дешифрование
            decrypted_data = self.crypto_manager.decrypt_data(encrypted_data, key)
            
            # Парсинг JSON
            program_data = json.loads(decrypted_data)
            
            # Валидация данных
            if not self.validate_program_structure(program_data):
                raise ValueError("Invalid program structure")
                
            # Проверка подписи
            if not self.validate_signature(program_data):
                raise ValueError("Invalid signature")
                
            # Проверка целостности
            if not self.verify_integrity(program_data):
                raise ValueError("Integrity check failed")
                
            # Кэширование загруженной программы
            program_id = program_data.get('metadata', {}).get('id', filepath)
            self.loaded_programs[program_id] = program_data
            
            return program_data
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Program file not found: {filepath}")
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in program file")
        except Exception as e:
            raise e
            
    def validate_program_structure(self, program_data):
        """
        Валидация структуры программы
        """
        required_sections = ['metadata', 'config', 'imports', 'functions', 'setup', 'loop_logic']
        
        for section in required_sections:
            if section not in program_data:
                return False
                
        # Проверка типов данных
        if not isinstance(program_data['metadata'], dict):
            return False
        if not isinstance(program_data['config'], dict):
            return False
        if not isinstance(program_data['imports'], list):
            return False
        if not isinstance(program_data['functions'], list):
            return False
        if not isinstance(program_data['setup'], list):
            return False
        if not isinstance(program_data['loop_logic'], list):
            return False
            
        return True
        
    def validate_signature(self, program_data):
        """
        Проверка цифровой подписи
        """
        metadata = program_data.get('metadata', {})
        signature = metadata.get('signature')
        
        if not signature:
            return False
            
        # Извлекаем данные для проверки подписи
        data_to_verify = {
            'version': metadata.get('version'),
            'timestamp': metadata.get('timestamp'),
            'checksum': metadata.get('checksum'),
            'author': metadata.get('author'),
            'description': metadata.get('description'),
            'config': program_data.get('config'),
            'imports': program_data.get('imports'),
            'functions': program_data.get('functions'),
            'setup': program_data.get('setup'),
            'loop_logic': program_data.get('loop_logic')
        }
        
        # Преобразуем в строку для проверки подписи
        data_str = json.dumps(data_to_verify, sort_keys=True)
        
        # Проверяем подпись
        try:
            result = self.security_checker.verify_ed25519_signature(
                data_str.encode('utf-8'), 
                bytes.fromhex(signature), 
                self.security_checker.get_public_key()
            )
            return result
        except:
            return False
            
    def verify_integrity(self, program_data):
        """
        Проверка целостности данных
        """
        metadata = program_data.get('metadata', {})
        stored_checksum = metadata.get('checksum')
        
        if not stored_checksum:
            return False
            
        # Создаем копию данных без чексуммы для проверки
        data_to_check = program_data.copy()
        metadata_copy = metadata.copy()
        metadata_copy.pop('checksum', None)
        data_to_check['metadata'] = metadata_copy
        
        # Вычисляем контрольную сумму
        data_str = json.dumps(data_to_check, sort_keys=True)
        computed_checksum = self.crypto_manager.hash_data(data_str)
        
        return stored_checksum == computed_checksum
        
    def load_encrypted_program(self, filepath, key):
        """
        Загрузка зашифрованной программы
        """
        return self.load_program(filepath, key)
        
    def cache_program(self, program_id, program_data):
        """
        Кэширование программы
        """
        self.loaded_programs[program_id] = program_data
        # Ограничиваем размер кэша
        if len(self.loaded_programs) > 10:  # Ограничение в 10 программ
            oldest_key = next(iter(self.loaded_programs))
            del self.loaded_programs[oldest_key]
            
    def get_cached_program(self, program_id):
        """
        Получение закэшированной программы
        """
        return self.loaded_programs.get(program_id)
        
    def clear_cache(self):
        """
        Очистка кэша программ
        """
        self.loaded_programs.clear()
        self.validation_cache.clear()
        gc.collect()
        
    def validate_permissions(self, program_data):
        """
        Проверка разрешений программы
        """
        config = program_data.get('config', {})
        permissions = config.get('permissions', [])
        
        # Определяем безопасные разрешения
        safe_permissions = ['gpio', 'time', 'math', 'struct', 'json']
        
        for perm in permissions:
            if perm not in safe_permissions:
                return False
                
        return True
        
    def get_program_metadata(self, program_data):
        """
        Извлечение метаданных программы
        """
        return program_data.get('metadata', {})
        
    def get_program_config(self, program_data):
        """
        Извлечение конфигурации программы
        """
        return program_data.get('config', {})
        
    def validate_runtime_constraints(self, program_data):
        """
        Проверка ограничений времени выполнения
        """
        config = program_data.get('config', {})
        
        # Проверяем лимиты
        runtime_limit = config.get('runtime_limit_ms', 5000)
        memory_limit = config.get('memory_limit_kb', 50)
        
        # Эти значения должны быть разумными
        if runtime_limit <= 0 or runtime_limit > 30000:  # Максимум 30 секунд
            return False
        if memory_limit <= 0 or memory_limit > 100:  # Максимум 100 KB
            return False
            
        return True


# Пример использования:
if __name__ == "__main__":
    loader = ProgramLoader()
    
    # Пример валидации структуры программы
    sample_program = {
        "metadata": {
            "version": "1.0",
            "signature": "sample_signature",
            "timestamp": "2023-01-01T00:00:00Z",
            "checksum": "sample_checksum",
            "author": "test",
            "description": "test program"
        },
        "config": {
            "runtime_limit_ms": 1000,
            "memory_limit_kb": 25,
            "permissions": ["gpio", "time"]
        },
        "imports": ["import machine", "import time"],
        "functions": ["def test():", "    return 42"],
        "setup": ["print('Setup')"],
        "loop_logic": ["result = test()", "print(result)"]
    }
    
    print("Structure validation:", loader.validate_program_structure(sample_program))
    print("Runtime constraints validation:", loader.validate_runtime_constraints(sample_program))
    print("Permissions validation:", loader.validate_permissions(sample_program))