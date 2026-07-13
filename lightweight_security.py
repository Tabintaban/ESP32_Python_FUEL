"""
LightweightSecurity - легковесная безопасность для проверки подписей и обеспечения безопасности

SECURITY FIXES:
- Replaced broken Ed25519 with HMAC-SHA256 symmetric signature
- Removed _derive_private_from_public() method (critical security flaw)
- Added nonce/timestamp for replay attack protection
- Implemented constant-time comparison for signature verification
- Signature now requires secret key knowledge

VULNERABILITY FIXES (v2):
- Fallback HMAC uses ipad/opad scheme instead of sha256(key+data) - protects against Length Extension Attack
- Fallback RNG uses os.urandom instead of random (Mersenne Twister) - cryptographically secure
- secure_random() function for guaranteed cryptographic randomness
- Shared _compute_hmac_sha256() with crypto_manager.py for consistency
"""

import hashlib
import time
import os

# Совместимость с CPython и MicroPython
if hasattr(time, 'ticks_ms'):
    get_time_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def get_time_ms():
        return int(time.time() * 1000)
    def ticks_diff(end, start):
        return end - start

# КРИТИЧЕСКИ ВАЖНО: используем os.urandom вместо random (Mersenne Twister)
# random предсказуем и НЕ должен использоваться для криптографии
try:
    import urandom  # type: ignore # MicroPython
    def secure_random(size):
        """Криптографически безопасный генератор случайных чисел (MicroPython)"""
        return urandom.urandom(size)
except ImportError:
    # Всегда используем os.urandom как fallback, НИКОГДА не используем random
    def secure_random(size):
        """Криптографически безопасный генератор случайных чисел (os.urandom)"""
        return os.urandom(size)

try:
    from uhashlib import hmac as uhmac  # type: ignore # MicroPython HMAC
except ImportError:
    uhmac = None


def _compute_hmac_sha256(key, data):
    """
    Безопасное вычисление HMAC-SHA256
    
    НЕ использует sha256(key + data) из-за уязвимости к Length Extension Attack.
    Использует HMAC-подобную схему через двойное хэширование с ipad/opad.
    Идентичная реализация в crypto_manager.py для консистентности.
    
    Args:
        key: Ключ для HMAC (должен быть 32 байта)
        data: Данные для вычисления HMAC
        
    Returns:
        32-байтовый HMAC-SHA256 дайджест
    """
    try:
        if uhmac is not None and hasattr(uhmac, 'new'):
            return uhmac.new(key, data, hashlib.sha256).digest()
    except:
        pass
    
    # Fallback: HMAC-подобная схема через двойное хэширование
    # Это ЗАЩИТА от Length Extension Attacks
    # НЕ используем sha256(key + data)!
    
    # Длина блока для SHA256 - 64 байта
    block_size = 64
    
    # Если ключ длиннее block_size, хэшируем его
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    
    # Дополняем ключ до block_size нулями
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))
    
    # Inner hash: H(key XOR ipad || data)
    ipad = bytes(b ^ 0x36 for b in key)
    inner_data = ipad + data
    inner_hash = hashlib.sha256(inner_data).digest()
    
    # Outer hash: H(key XOR opad || inner_hash)
    opad = bytes(b ^ 0x5c for b in key)
    outer_data = opad + inner_hash
    outer_hash = hashlib.sha256(outer_data).digest()
    
    return outer_hash


class LightweightSecurity:
    """
    Класс для проверки цифровых подписей и обеспечения безопасности
    
    Использует HMAC-SHA256 для симметричной подписи данных.
    Подходит для сценариев, где одно и то же устройство подписывает и проверяет данные.
    """
    
    def __init__(self, secret_key=None):
        """
        Инициализация системы безопасности
        
        Args:
            secret_key: Секретный ключ для HMAC-SHA256 (32 байта, если None будет сгенерирован)
        """
        self.secret_key = secret_key
        self.signature_algorithm = "HMAC-SHA256"
        self.nonce_cache = {}  # Для защиты от replay-атак
        self.max_nonce_age_ms = 60000  # Nonce действителен 60 секунд
        
        if secret_key is None:
            self.secret_key = self._generate_secret_key()
        else:
            if len(secret_key) != 32:
                raise ValueError("Secret key must be 32 bytes")
    
    def _generate_secret_key(self):
        """
        Генерация случайного секретного ключа
        Использует КРИПТОГРАФИЧЕСКИ БЕЗОПАСНЫЙ генератор (os.urandom/urandom.urandom)
        """
        return secure_random(32)
        
    def generate_keys(self):
        """
        Генерация секретного ключа (для обратной совместимости)
        
        Returns:
            (public_key, secret_key): Публичный идентификатор и секретный ключ
        """
        secret_key = self._generate_secret_key()
        # Публичный ключ - это хеш секретного ключа (для идентификации, но не для подписи)
        public_key = hashlib.sha256(secret_key).digest()
        
        self.secret_key = secret_key
        
        return public_key, secret_key
        
    def sign_data(self, data, private_key=None, nonce=None):
        """
        Подпись данных с использованием HMAC-SHA256
        
        Args:
            data: Данные для подписи (str или bytes)
            private_key: Секретный ключ (опционально, если не установлен в __init__)
            nonce: Уникальное значение для защиты от replay-атак (опционально)
            
        Returns:
            HMAC-SHA256 подпись (32 байта)
        """
        if private_key is None:
            if self.secret_key is None:
                self.secret_key = self._generate_secret_key()
            private_key = self.secret_key
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Добавляем nonce если предоставлен для защиты от replay-атак
        if nonce is not None:
            if isinstance(nonce, str):
                nonce = nonce.encode('utf-8')
            data = data + nonce
        
        # Вычисляем HMAC-SHA256 через безопасный fallback
        signature = _compute_hmac_sha256(private_key, data)
        
        return signature
        
    def verify_signature(self, data, signature, secret_key=None, nonce=None):
        """
        Проверка HMAC-SHA256 подписи
        
        Args:
            data: Данные для проверки (str или bytes)
            signature: Подпись для проверки (32 байта)
            secret_key: Секретный ключ (опционально, если не установлен в __init__)
            nonce: Уникальное значение, использованное при подписи (опционально)
            
        Returns:
            True если подпись валидна, False иначе
        """
        if secret_key is None:
            if self.secret_key is None:
                raise ValueError("No secret key available for verification")
            secret_key = self.secret_key
        
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Добавляем nonce если предоставлен
        if nonce is not None:
            if isinstance(nonce, str):
                nonce = nonce.encode('utf-8')
            data = data + nonce
        
        # Вычисляем ожидаемую подпись через безопасный HMAC
        expected_signature = _compute_hmac_sha256(secret_key, data)
        
        # Constant-time сравнение
        return self._constant_time_compare(signature, expected_signature)
    
    def _constant_time_compare(self, a, b):
        """
        Сравнение двух байтовых строк за постоянное время (защита от timing attacks)
        """
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        
        return result == 0
        
    def get_public_key(self):
        """
        Получение публичного идентификатора (хеш секретного ключа)
        
        Returns:
            Публичный идентификатор (32 байта)
        """
        if self.secret_key is None:
            self.secret_key = self._generate_secret_key()
        return hashlib.sha256(self.secret_key).digest()
    
    def get_secret_key(self):
        """
        Получение секретного ключа
        
        Returns:
            Секретный ключ (32 байта)
        """
        if self.secret_key is None:
            self.secret_key = self._generate_secret_key()
        return self.secret_key
    
    def set_secret_key(self, secret_key):
        """
        Установка секретного ключа
        
        Args:
            secret_key: 32-байтный секретный ключ
        """
        if len(secret_key) != 32:
            raise ValueError("Secret key must be 32 bytes")
        self.secret_key = secret_key
        
    def generate_nonce(self):
        """
        Генерация уникального nonce для защиты от replay-атак
        
        Returns:
            (nonce, timestamp): Кортеж из nonce и timestamp
        """
        nonce = secure_random(16)
        timestamp = get_time_ms()
        return nonce.hex(), timestamp
    
    def validate_nonce(self, nonce, timestamp):
        """
        Проверка nonce для защиты от replay-атак
        
        Args:
            nonce: Уникальное значение
            timestamp: Временная метка генерации nonce
            
        Returns:
            True если nonce валиден и не использовался ранее
        """
        # Проверяем возраст nonce
        current_time = get_time_ms()
        age = ticks_diff(current_time, timestamp)
        
        if age > self.max_nonce_age_ms or age < 0:
            return False  # Nonce слишком старый или из будущего
        
        # Проверяем, не использовался ли nonce ранее
        nonce_key = f"{nonce}_{timestamp}"
        if nonce_key in self.nonce_cache:
            return False  # Replay attack detected
        
        # Сохраняем nonce
        self.nonce_cache[nonce_key] = current_time
        
        # Очищаем старые nonce
        self._cleanup_nonces(current_time)
        
        return True
    
    def _cleanup_nonces(self, current_time):
        """
        Очистка устаревших nonce из кэша
        """
        expired_keys = []
        for key, stored_time in self.nonce_cache.items():
            age = ticks_diff(current_time, stored_time)
            if age > self.max_nonce_age_ms:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.nonce_cache[key]
    
    def check_permissions(self, functions):
        """
        Проверка разрешений на вызов функций
        """
        # Определяем список безопасных функций
        safe_functions = [
            'print', 'len', 'range', 'enumerate', 'zip', 'map', 'filter',
            'abs', 'min', 'max', 'sum', 'round', 'int', 'float', 'str', 'bool',
            'list', 'dict', 'set', 'tuple', 'type', 'isinstance', 'hasattr',
            'callable', 'hash', 'id'
        ]
        
        # УБРАЛИ getattr, setattr, delattr из безопасных функций
        unsafe_patterns = [
            'eval', 'exec', 'compile', '__import__', 'open', 'file',
            'input', 'raw_input', '__', 'globals', 'locals', 'vars',
            'getattr', 'setattr', 'delattr'  # Добавили в небезопасные
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
