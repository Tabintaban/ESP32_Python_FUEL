"""
CryptoManager - класс для шифрования/дешифрования данных с использованием AES-GCM и других криптографических алгоритмов
"""
import os
import json
from binascii import hexlify, unhexlify
from hashlib import sha256
import ustruct as struct  # type: ignore
try:
    from ucryptolib import aes  # type: ignore # MicroPython crypto module
except ImportError:
    # Заглушка для случаев, когда ucryptolib недоступен
    class MockAes:
        def __init__(self, key, mode, iv=None):
            self.key = key
            self.mode = mode
            self.iv = iv
        
        def encrypt(self, data):
            # Простая реализация для тестирования
            return bytes(d ^ self.key[i % len(self.key)] for i, d in enumerate(data))
        
        def decrypt(self, data):
            # Та же операция, что и шифрование в XOR
            return self.encrypt(data)
    
    aes = MockAes
    print("Warning: ucryptolib not available, using mock implementation")

try:
    import urandom  # type: ignore # MicroPython
except ImportError:
    import random as urandom  # Standard Python for testing

class CryptoManager:
    """
    Класс для шифрования и дешифрования данных с использованием AES-GCM
    """
    
    def __init__(self):
        # Размеры ключа и IV для AES
        self.key_size = 32  # 256-bit ключ
        self.iv_size = 12   # 96-bit IV для GCM
        
    def generate_key(self):
        """
        Генерация случайного ключа
        """
        return urandom.urandom(self.key_size)  # pylint: disable=no-member
        
    def pad_data(self, data):
        """
        Добавление PKCS7 padding к данным
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        pad_len = 16 - (len(data) % 16)
        return data + bytes([pad_len] * pad_len)
        
    def unpad_data(self, data):
        """
        Удаление PKCS7 padding из данных
        """
        pad_len = data[-1]
        return data[:-pad_len]
        
    def encrypt_aes_gcm(self, plaintext, key, associated_data=None):
        """
        Шифрование данных с использованием AES-GCM
        Возвращает: (ciphertext, auth_tag, iv)
        """
        # Генерация случайного IV
        iv = urandom.urandom(self.iv_size)  # pylint: disable=no-member
        
        # Создание объекта шифрования
        cipher = aes(key, 1, iv)  # AES.MODE_GCM эмулируется
        
        # Добавляем ассоциированные данные если есть
        if associated_data:
            # В реальной реализации AES-GCM нужно будет добавить associated_data
            pass
            
        # Шифрование данных
        padded_plaintext = self.pad_data(plaintext)
        ciphertext = cipher.encrypt(padded_plaintext)
        
        # Генерация имитовставки (в упрощённой форме)
        # В реальной реализации нужно использовать полноценный AES-GCM
        auth_tag = sha256(ciphertext + iv).digest()[:16]
        
        return ciphertext, auth_tag, iv
        
    def decrypt_aes_gcm(self, ciphertext, auth_tag, iv, key, associated_data=None):
        """
        Расшифровка данных с использованием AES-GCM
        """
        # Проверка имитовставки (в упрощённой форме)
        calculated_auth_tag = sha256(ciphertext + iv).digest()[:16]
        if calculated_auth_tag != auth_tag:
            raise ValueError("Authentication failed")
            
        # Создание объекта расшифровки
        cipher = aes(key, 1, iv)
        
        # Расшифровка
        padded_plaintext = cipher.decrypt(ciphertext)
        
        # Удаление padding
        plaintext = self.unpad_data(padded_plaintext)
        
        return plaintext
        
    def encrypt_data(self, data, key):
        """
        Шифрование данных
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        ciphertext, auth_tag, iv = self.encrypt_aes_gcm(data, key)
        
        # Возвращаем зашифрованные данные в виде словаря
        result = {
            'iv': hexlify(iv).decode(),
            'auth_tag': hexlify(auth_tag).decode(),
            'ciphertext': hexlify(ciphertext).decode()
        }
        
        return json.dumps(result)
        
    def decrypt_data(self, encrypted_data, key):
        """
        Дешифрование данных
        """
        if isinstance(encrypted_data, str):
            encrypted_data = json.loads(encrypted_data)
            
        iv = unhexlify(encrypted_data['iv'])
        auth_tag = unhexlify(encrypted_data['auth_tag'])
        ciphertext = unhexlify(encrypted_data['ciphertext'])
        
        plaintext = self.decrypt_aes_gcm(ciphertext, auth_tag, iv, key)
        
        return plaintext.decode('utf-8')
        
    def encrypt_file(self, filepath, key, output_filepath=None):
        """
        Шифрование файла
        """
        if output_filepath is None:
            output_filepath = filepath + '.enc'
            
        with open(filepath, 'r') as f:
            data = f.read()
            
        encrypted_data = self.encrypt_data(data, key)
        
        with open(output_filepath, 'w') as f:
            f.write(encrypted_data)
            
        return output_filepath
        
    def decrypt_file(self, filepath, key, output_filepath=None):
        """
        Расшифровка файла
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
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        return sha256(data).hexdigest()


# МикроПитоновая реализация AES-GCM (упрощенная)
class AESGCMEmulator:
    """
    Упрощенная эмуляция AES-GCM для MicroPython
    """
    
    def __init__(self, key):
        self.cipher = aes(key, 1)  # AES ECB mode
        
    def encrypt(self, plaintext, iv, aad=None):
        """
        Упрощенное шифрование (не настоящий GCM)
        """
        # Добавляем padding
        if len(plaintext) % 16 != 0:
            pad_len = 16 - (len(plaintext) % 16)
            plaintext += bytes([pad_len] * pad_len)
            
        # Шифруем
        ciphertext = self.cipher.encrypt(plaintext)
        
        # Генерируем простую аутентификационную метку
        tag = sha256(ciphertext + iv).digest()[:16]
        
        return ciphertext, tag
        
    def decrypt(self, ciphertext, iv, tag, aad=None):
        """
        Упрощенная расшифровка (не настоящий GCM)
        """
        # Проверяем тег
        calculated_tag = sha256(ciphertext + iv).digest()[:16]
        if calculated_tag != tag:
            raise ValueError("Authentication failed")
            
        # Расшифровываем
        plaintext = self.cipher.decrypt(ciphertext)
        
        # Удаляем padding
        if plaintext[-1] <= 16:  # Возможно padding
            pad_len = plaintext[-1]
            if all(b == pad_len for b in plaintext[-pad_len:]):
                plaintext = plaintext[:-pad_len]
                
        return plaintext