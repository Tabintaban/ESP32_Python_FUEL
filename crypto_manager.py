"""
CryptoManager - класс для шифрования/дешифрования данных с использованием AES-CTR + HMAC-SHA256 (Encrypt-then-MAC)

SECURITY FIXES:
- Replaced fake AES-GCM with proper AES-CTR encryption
- Added HMAC-SHA256 for authentication (Encrypt-then-MAC scheme)
- Implemented constant-time comparison for tag verification
- Separate keys for encryption and authentication
- Unique IV generation for each encryption

VULNERABILITY FIXES (v2):
- Fallback HMAC uses ipad/opad scheme instead of sha256(key+data) - protects against Length Extension Attack
- Fallback RNG uses os.urandom instead of random (Mersenne Twister) - cryptographically secure
- secure_random() function for guaranteed cryptographic randomness

VULNERABILITY FIXES (v3) - FAIL-SECURE:
- REMOVED MockAes (XOR pseudo-encryption) completely. XOR created a false sense
  of security and silently downgraded encryption when ucryptolib was missing.
- ucryptolib is now MANDATORY: if it cannot be imported, a stub raises
  RuntimeError on any use -> fail-secure instead of insecure fallback.
- CryptoManager.__init__() validates crypto availability up-front.
"""
import os
import json
from binascii import hexlify, unhexlify
from hashlib import sha256
try:
    import ustruct as struct  # type: ignore # MicroPython
except ImportError:
    import struct  # CPython

# === FAIL-SECURE AES IMPORT ===
# ucryptolib обязателен. Если его нет — НИКАКОЙ криптографии. Никаких
# XOR/моков, которые компрометируют данные: лучше жёсткий сбой (fail-secure),
# чем небезопасное выполнение.
_CRYPTO_AVAILABLE = True
try:
    from ucryptolib import aes  # type: ignore # MicroPython crypto module
except ImportError:
    _CRYPTO_AVAILABLE = False

    class aes:
        """
        Fail-secure заглушка вместо небезопасного MockAes.
        Любая попытка использовать AES без ucryptolib немедленно падает —
        это предотвращает тихую деградацию до XOR-шифрования.
        """
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: 'ucryptolib' is not available. "
                "AES encryption is disabled. Do not use in production. "
                "Please flash a MicroPython firmware that includes ucryptolib."
            )

        def encrypt(self, *args, **kwargs):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: 'ucryptolib' is not available. "
                "AES encryption is disabled."
            )

        def decrypt(self, *args, **kwargs):
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: 'ucryptolib' is not available. "
                "AES encryption is disabled."
            )

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
    
    Args:
        key: Ключ для HMAC (должен быть 32 байта)
        data: Данные для вычисления HMAC
        
    Returns:
        32-байтовый HMAC-SHA256 дайджест
    """
    try:
        if uhmac is not None and hasattr(uhmac, 'new'):
            return uhmac.new(key, data, sha256).digest()
    except:
        pass
    
    # Fallback: HMAC-подобная схема через двойное хэширование
    # Это ЗАЩИТА от Length Extension Attacks
    # НЕ используем sha256(key + data)!
    
    # Длина блока для SHA256 - 64 байта
    block_size = 64
    
    # Если ключ длиннее block_size, хэшируем его
    if len(key) > block_size:
        key = sha256(key).digest()
    
    # Дополняем ключ до block_size нулями
    if len(key) < block_size:
        key = key + b'\x00' * (block_size - len(key))
    
    # Inner hash: H(key XOR ipad || data)
    ipad = bytes(b ^ 0x36 for b in key)
    inner_data = ipad + data
    inner_hash = sha256(inner_data).digest()
    
    # Outer hash: H(key XOR opad || inner_hash)
    opad = bytes(b ^ 0x5c for b in key)
    outer_data = opad + inner_hash
    outer_hash = sha256(outer_data).digest()
    
    return outer_hash


class CryptoManager:
    """
    Класс для шифрования и дешифрования данных с использованием AES-CTR + HMAC-SHA256
    
    Использует схему Encrypt-then-MAC для обеспечения аутентификации:
    1. Шифрование данных с помощью AES-CTR
    2. Вычисление HMAC-SHA256 зашифрованных данных + IV
    3. При расшифровке: сначала проверка HMAC, затем расшифровка
    """
    
    def __init__(self, encryption_key=None, hmac_key=None):
        """
        Инициализация криптографического менеджера

        Args:
            encryption_key: 32-байтный ключ для AES-256 (если None, будет сгенерирован)
            hmac_key: 32-байтный ключ для HMAC-SHA256 (если None, будет сгенерирован)

        Raises:
            RuntimeError: Если ucryptolib недоступен (fail-secure).
        """
        # === FAIL-SECURE CHECK ===
        # Проверяем наличие реальной криптографии СРАЗУ при создании менеджера,
        # а не в момент первого encrypt/decrypt — пользователь получает понятную
        # ошибку до того, как данные будут куда-либо записаны.
        if not _CRYPTO_AVAILABLE:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Cannot initialize CryptoManager - "
                "'ucryptolib' is not available in this MicroPython firmware. "
                "Encryption/decryption is DISABLED (fail-secure). "
                "Flash a firmware that includes ucryptolib to enable crypto."
            )

        # Размеры ключей и IV для AES-256-CTR
        self.aes_key_size = 32  # 256-bit ключ для AES
        self.hmac_key_size = 32  # 256-bit ключ для HMAC
        self.iv_size = 16       # 128-bit IV для CTR mode
        
        # Генерация ключей если не предоставлены
        if encryption_key is None:
            self.encryption_key = self._generate_key(self.aes_key_size)
        else:
            if len(encryption_key) != self.aes_key_size:
                raise ValueError(f"Encryption key must be {self.aes_key_size} bytes")
            self.encryption_key = encryption_key
            
        if hmac_key is None:
            self.hmac_key = self._generate_key(self.hmac_key_size)
        else:
            if len(hmac_key) != self.hmac_key_size:
                raise ValueError(f"HMAC key must be {self.hmac_key_size} bytes")
            self.hmac_key = hmac_key
    
    def _generate_key(self, size):
        """
        Генерация случайного ключа заданного размера
        Использует КРИПТОГРАФИЧЕСКИ БЕЗОПАСНЫЙ генератор (os.urandom/urandom.urandom)
        """
        return secure_random(size)
    
    def generate_key(self):
        """
        Генерация случайного ключа (для обратной совместимости)
        Возвращает кортеж (encryption_key, hmac_key)
        """
        return self._generate_key(self.aes_key_size), self._generate_key(self.hmac_key_size)
        
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
        
    def encrypt_aes_ctr_hmac(self, plaintext, associated_data=None):
        """
        Шифрование данных с использованием AES-CTR + HMAC-SHA256 (Encrypt-then-MAC)
        
        Args:
            plaintext: Данные для шифрования (bytes или str)
            associated_data: Дополнительные данные для аутентификации (опционально)
            
        Returns:
            (ciphertext, auth_tag, iv): Зашифрованные данные, тег аутентификации, IV
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        # Генерация уникального IV для каждого шифрования
        iv = secure_random(self.iv_size)
        
        # Создание объекта шифрования AES-CTR (mode 2)
        cipher = aes(self.encryption_key, 2, iv)
        
        # Шифрование данных (CTR mode не требует padding)
        ciphertext = cipher.encrypt(plaintext)
        
        # Вычисление HMAC-SHA256 зашифрованных данных + IV (+ associated_data если есть)
        hmac_data = ciphertext + iv
        if associated_data:
            if isinstance(associated_data, str):
                associated_data = associated_data.encode('utf-8')
            hmac_data += associated_data
        
        # Используем безопасный HMAC (защита от Length Extension Attack)
        auth_tag = _compute_hmac_sha256(self.hmac_key, hmac_data)
        
        return ciphertext, auth_tag, iv
        
    def decrypt_aes_ctr_hmac(self, ciphertext, auth_tag, iv, associated_data=None):
        """
        Расшифровка данных с использованием AES-CTR + HMAC-SHA256
        
        Args:
            ciphertext: Зашифрованные данные
            auth_tag: Тег аутентификации
            iv: Вектор инициализации
            associated_data: Дополнительные данные для аутентификации (опционально)
            
        Returns:
            Расшифрованные данные
            
        Raises:
            ValueError: Если аутентификация не прошла (подмена данных)
        """
        # СНАЧАЛА проверяем тег аутентификации (Encrypt-then-MAC)
        hmac_data = ciphertext + iv
        if associated_data:
            if isinstance(associated_data, str):
                associated_data = associated_data.encode('utf-8')
            hmac_data += associated_data
        
        # Вычисление ожидаемого тега через безопасный HMAC
        calculated_auth_tag = _compute_hmac_sha256(self.hmac_key, hmac_data)
        
        # Constant-time сравнение тегов
        if not self._constant_time_compare(calculated_auth_tag, auth_tag):
            raise ValueError("Authentication failed: data may have been tampered with")
        
        # ТОЛЬКО ПОСЛЕ успешной проверки аутентификации расшифровываем
        cipher = aes(self.encryption_key, 2, iv)
        plaintext = cipher.decrypt(ciphertext)
        
        return plaintext
        
    def encrypt_data(self, data, key=None):
        """
        Шифрование данных с использованием AES-CTR + HMAC-SHA256
        
        Args:
            data: Данные для шифрования (str или bytes)
            key: Ключ шифрования (для обратной совместимости, игнорируется если установлены ключи в __init__)
            
        Returns:
            JSON-строка с зашифрованными данными
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        ciphertext, auth_tag, iv = self.encrypt_aes_ctr_hmac(data)
        
        # Возвращаем зашифрованные данные в виде словаря (сохраняем формат для обратной совместимости)
        result = {
            'iv': hexlify(iv).decode(),
            'auth_tag': hexlify(auth_tag).decode(),
            'ciphertext': hexlify(ciphertext).decode()
        }
        
        return json.dumps(result)
        
    def decrypt_data(self, encrypted_data, key=None):
        """
        Дешифрование данных с проверкой аутентификации
        
        Args:
            encrypted_data: Зашифрованные данные (JSON-строка или dict)
            key: Ключ шифрования (для обратной совместимости, игнорируется если установлены ключи в __init__)
            
        Returns:
            Расшифрованные данные (str)
            
        Raises:
            ValueError: Если аутентификация не прошла
        """
        if isinstance(encrypted_data, str):
            encrypted_data = json.loads(encrypted_data)
            
        iv = unhexlify(encrypted_data['iv'])
        auth_tag = unhexlify(encrypted_data['auth_tag'])
        ciphertext = unhexlify(encrypted_data['ciphertext'])
        
        plaintext = self.decrypt_aes_ctr_hmac(ciphertext, auth_tag, iv)
        
        return plaintext.decode('utf-8')
        
    def encrypt_file(self, filepath, key=None, output_filepath=None):
        """
        Шифрование файла
        
        Args:
            filepath: Путь к исходному файлу
            key: Ключ шифрования (опционально, если не установлен в __init__)
            output_filepath: Путь к зашифрованному файлу (опционально)
            
        Returns:
            Путь к зашифрованному файлу
        """
        if output_filepath is None:
            output_filepath = filepath + '.enc'
            
        with open(filepath, 'r') as f:
            data = f.read()
            
        encrypted_data = self.encrypt_data(data, key)
        
        with open(output_filepath, 'w') as f:
            f.write(encrypted_data)
            
        return output_filepath
        
    def decrypt_file(self, filepath, key=None, output_filepath=None):
        """
        Расшифровка файла
        
        Args:
            filepath: Путь к зашифрованному файлу
            key: Ключ шифрования (опционально, если не установлен в __init__)
            output_filepath: Путь к расшифрованному файлу (опционально)
            
        Returns:
            Путь к расшифрованному файлу
        """
        if output_filepath is None:
            output_filepath = filepath.replace('.enc', '') + '.dec'
            
        with open(filepath, 'r') as f:
            encrypted_data = f.read()
            
        decrypted_data = self.decrypt_data(encrypted_data, key)
        
        with open(output_filepath, 'w') as f:
            f.write(decrypted_data)
            
        return output_filepath
        
    def hash_data(self, data):
        """
        Хеширование данных с использованием SHA-256
        
        Args:
            data: Данные для хеширования (str или bytes)
            
        Returns:
            Hex-строка хеша SHA-256
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return sha256(data).hexdigest()
    
    def get_keys(self):
        """
        Получение текущих ключей (для сохранения/экспорта)
        
        Returns:
            (encryption_key, hmac_key): Кортеж ключей
        """
        return self.encryption_key, self.hmac_key
    
    def set_keys(self, encryption_key, hmac_key):
        """
        Установка новых ключей
        
        Args:
            encryption_key: 32-байтный ключ для AES
            hmac_key: 32-байтный ключ для HMAC
        """
        if len(encryption_key) != self.aes_key_size:
            raise ValueError(f"Encryption key must be {self.aes_key_size} bytes")
        if len(hmac_key) != self.hmac_key_size:
            raise ValueError(f"HMAC key must be {self.hmac_key_size} bytes")
        
        self.encryption_key = encryption_key
        self.hmac_key = hmac_key
