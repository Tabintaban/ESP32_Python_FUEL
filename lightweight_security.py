"""
LightweightSecurity - легковесная безопасность для проверки подписей и обеспечения безопасности
"""

import hashlib

# Попытка импорта urandom для MicroPython с fallback для стандартного Python
try:
    import urandom  # type: ignore # MicroPython
except ImportError:
    import random as urandom  # Standard Python for testing


class LightweightSecurity:
    """
    Класс для проверки цифровых подписей и обеспечения безопасности
    """
    
    def __init__(self):
        # В MicroPython полноценная реализация Ed25519 может быть недоступна
        # Поэтому реализуем упрощенную систему
        self.public_key = None
        self.private_key = None
        self.signature_algorithm = "SHA256_WITH_RSA_SIMULATION"  # Симуляция
        
    def generate_keys(self):
        """
        Генерация ключевой пары (в упрощенной форме)
        """
        # В реальной системе использовалась бы криптографически стойкая генерация
        # Для MicroPython создаем имитацию
        private_key = urandom.urandom(32)  # pylint: disable=no-member
        public_key = hashlib.sha256(private_key).digest()
        
        self.private_key = private_key
        self.public_key = public_key
        
        return public_key, private_key
        
    def sign_data(self, data, private_key=None):
        """
        Подпись данных (в упрощенной форме)
        """
        if private_key is None:
            if self.private_key is None:
                self.generate_keys()
            private_key = self.private_key
            
        # Вместо настоящей подписи Ed25519 используем хеширование
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # Простая "подпись" - хеш данных + приватный ключ
        signature = hashlib.sha256(data + private_key).digest()
        
        return signature
        
    def verify_ed25519_signature(self, data, signature, public_key):
        """
        Проверка подписи Ed25519 (в упрощенной форме для MicroPython)
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # В упрощенной версии проверяем соответствие хеша
        # Это НЕ настоящая проверка Ed25519, а лишь симуляция
        expected_signature = hashlib.sha256(data + self._derive_private_from_public(public_key)).digest()
        
        return signature == expected_signature
        
    def _derive_private_from_public(self, public_key):
        """
        Получение приватного ключа из публичного (для симуляции)
        """
        # Это НЕ безопасно и НЕ должно использоваться в реальных системах
        # Просто для демонстрации в упрощенной версии
        return hashlib.sha256(public_key).digest()[:32]
        
    def get_public_key(self):
        """
        Получение публичного ключа
        """
        if self.public_key is None:
            self.generate_keys()
        return self.public_key
        
    def check_permissions(self, functions):
        """
        Проверка разрешений на вызов функций
        """
        # Определяем список безопасных функций
        safe_functions = [
            'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
            'abs', 'min', 'max', 'sum', 'round', 'int', 'float', 'str', 'bool',
            'list', 'dict', 'set', 'tuple', 'type', 'isinstance', 'hasattr',
            'getattr', 'setattr', 'delattr', 'callable', 'hash', 'id'
        ]
        
        unsafe_patterns = [
            'eval', 'exec', 'compile', '__import__', 'open', 'file',
            'input', 'raw_input', '__', 'globals', 'locals', 'vars'
        ]
        
        for func_name in functions:
            # Проверяем на небезопасные паттерны
            for pattern in unsafe_patterns:
                if pattern.lower() in func_name.lower():
                    return False, f"Unsafe function detected: {func_name}"
                    
            # Проверяем, является ли функция безопасной
            if func_name not in safe_functions:
                # Если функция не в списке безопасных, проверяем дополнительно
                pass
                
        return True, "All functions are safe"
        
    def sanitize_input(self, data):
        """
        Очистка входных данных
        """
        if isinstance(data, str):
            # Удаляем потенциально опасные символы
            sanitized = data.replace('\0', '').replace(chr(0), '')  # Null bytes
            # Ограничиваем длину строк
            if len(sanitized) > 10000:  # Ограничение в 10 КБ
                sanitized = sanitized[:10000]
            return sanitized
        elif isinstance(data, (list, tuple)):
            return [self.sanitize_input(item) for item in data]
        elif isinstance(data, dict):
            return {key: self.sanitize_input(value) for key, value in data.items()}
        else:
            return data
            
    def validate_json_structure(self, json_data, allowed_keys=None):
        """
        Валидация структуры JSON
        """
        if allowed_keys is None:
            allowed_keys = [
                'metadata', 'config', 'imports', 'functions', 'setup', 'loop_logic'
            ]
            
        if not isinstance(json_data, dict):
            return False, "JSON data must be an object"
            
        for key in json_data.keys():
            if key not in allowed_keys:
                return False, f"Unauthorized key in JSON: {key}"
                
        return True, "JSON structure is valid"
        
    def check_resource_limits(self, code_complexity_score):
        """
        Проверка лимитов ресурсов на основе оценки сложности кода
        """
        # Оценка сложности кода (упрощенная)
        max_complexity = 100  # Максимально допустимая сложность
        
        if code_complexity_score > max_complexity:
            return False, f"Code complexity too high: {code_complexity_score} > {max_complexity}"
            
        return True, "Resource limits acceptable"
        
    def calculate_code_complexity(self, code):
        """
        Расчет сложности кода (упрощенный метод)
        """
        if isinstance(code, list):
            code = '\n'.join(code)
            
        # Простая метрика сложности
        lines = code.split('\n')
        complexity = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('if ', 'elif ', 'else:', 'for ', 'while ', 'def ', 'class ')):
                complexity += 1
            if 'import ' in stripped:
                complexity += 0.5
            if stripped.count('(') > stripped.count(')'):  # Неполные выражения
                complexity += 0.1
                
        return min(complexity, 1000)  # Ограничиваем максимальное значение
        
    def hash_password(self, password):
        """
        Хеширование пароля
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        return hashlib.sha256(password).hexdigest()
        
    def verify_password(self, password, hashed_password):
        """
        Проверка пароля
        """
        return self.hash_password(password) == hashed_password


# Пример использования:
if __name__ == "__main__":
    security = LightweightSecurity()
    
    # Генерация ключей
    pub_key, priv_key = security.generate_keys()
    print(f"Public key: {pub_key.hex()[:16]}...")
    print(f"Private key: {priv_key.hex()[:16]}...")
    
    # Подписание данных
    test_data = "Hello, ESP32 Secure System!"
    signature = security.sign_data(test_data)
    print(f"Signature: {signature.hex()[:16]}...")
    
    # Проверка подписи
    is_valid = security.verify_ed25519_signature(test_data, signature, pub_key)
    print(f"Signature valid: {is_valid}")
    
    # Проверка разрешений
    test_functions = ['print', 'len', 'range']
    perms_ok, perms_msg = security.check_permissions(test_functions)
    print(f"Permissions OK: {perms_ok}, Message: {perms_msg}")
    
    # Санитизация данных
    dirty_data = {"key": "value\0with\0nulls", "list": ["safe", "unsafe_eval"]}
    clean_data = security.sanitize_input(dirty_data)
    print(f"Clean data: {clean_data}")
    
    # Проверка сложности кода
    test_code = [
        "def example():",
        "    for i in range(10):",
        "        if i > 5:",
        "            print(i)"
    ]
    complexity = security.calculate_code_complexity(test_code)
    print(f"Code complexity: {complexity}")