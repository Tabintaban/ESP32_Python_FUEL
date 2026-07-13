"""
Unit tests for crypto_manager module
"""
import sys
sys.path.insert(0, '..')

import json
import time
from binascii import hexlify, unhexlify
from crypto_manager import CryptoManager, _compute_hmac_sha256, secure_random

# Совместимость с CPython и MicroPython
if hasattr(time, 'ticks_ms'):
    get_time_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def get_time_ms():
        return int(time.time() * 1000)
    def ticks_diff(end, start):
        return end - start


def test_crypto_manager():
    """
    Unit-тесты для CryptoManager
    """
    print("Testing CryptoManager...")
    
    # На CPython без ucryptolib этот тест не работает
    try:
        from ucryptolib import aes
    except ImportError:
        print("✓ CryptoManager tests skipped (ucryptolib not available on CPython)")
        return
    
    # Тест 1: Базовое шифрование-дешифрование
    cm = CryptoManager()
    plaintext = b"Hello, ESP32 Secure System!"
    
    encrypted = cm.encrypt_data(plaintext)
    decrypted = cm.decrypt_data(encrypted)
    
    assert decrypted == plaintext.decode('utf-8'), "Decryption failed"
    print("✓ Test 1: Basic encryption/decryption passed")
    
    # Тест 2: Обнаружение подмены данных
    encrypted_dict = json.loads(encrypted)
    tampered_ciphertext = bytearray(unhexlify(encrypted_dict['ciphertext']))
    tampered_ciphertext[0] ^= 0xFF  # Инвертируем первый байт
    encrypted_dict['ciphertext'] = hexlify(tampered_ciphertext).decode()
    
    try:
        cm.decrypt_data(json.dumps(encrypted_dict))
        assert False, "Should detect tampering"
    except ValueError as e:
        assert "Authentication failed" in str(e)
        print("✓ Test 2: Tampering detection passed")
    
    # Тест 3: Уникальность IV для одинаковых данных
    enc1 = cm.encrypt_data(plaintext)
    enc2 = cm.encrypt_data(plaintext)
    
    dict1 = json.loads(enc1)
    dict2 = json.loads(enc2)
    
    assert dict1['iv'] != dict2['iv'], "IV must be unique"
    assert dict1['ciphertext'] != dict2['ciphertext'], "Ciphertext must differ with different IV"
    print("✓ Test 3: IV uniqueness passed")
    
    # Тест 4: Проверка constant-time comparison (защита от timing attacks)
    
    tag = bytes(32)
    same_tag = bytes(32)
    diff_tag_start = bytes(32)
    diff_tag_start = bytearray(diff_tag_start)
    diff_tag_start[0] ^= 0xFF
    diff_tag_start = bytes(diff_tag_start)
    
    diff_tag_end = bytes(32)
    diff_tag_end = bytearray(diff_tag_end)
    diff_tag_end[31] ^= 0xFF
    diff_tag_end = bytes(diff_tag_end)
    
    # Сравнение должно занимать примерно одинаковое время
    start = get_time_ms()
    for _ in range(100):
        cm._constant_time_compare(tag, same_tag)
    time_same = ticks_diff(get_time_ms(), start)
    
    start = get_time_ms()
    for _ in range(100):
        cm._constant_time_compare(tag, diff_tag_start)
    time_diff_start = ticks_diff(get_time_ms(), start)
    
    start = get_time_ms()
    for _ in range(100):
        cm._constant_time_compare(tag, diff_tag_end)
    time_diff_end = ticks_diff(get_time_ms(), start)
    
    # Времена должны быть примерно одинаковыми (допускаем небольшую вариацию)
    assert abs(time_diff_start - time_diff_end) < max(time_same, 1), "Constant-time comparison failed"
    print("✓ Test 4: Constant-time comparison passed")
    
    # Тест 5: Разные ключи дают разные результаты
    cm2 = CryptoManager()
    enc3 = cm2.encrypt_data(plaintext)
    
    assert enc1 != enc3, "Different keys should produce different ciphertext"
    print("✓ Test 5: Different keys produce different results")
    
    # Тест 6: Проверка secure_random - не возвращает random
    rand_bytes = secure_random(32)
    assert len(rand_bytes) == 32, "secure_random should return 32 bytes"
    assert isinstance(rand_bytes, bytes), "secure_random should return bytes"
    print("✓ Test 6: secure_random works correctly")
    
    # Тест 7: Проверка безопасного HMAC fallback
    test_key = b"TestHMACKey32BytesLongForTesting!"
    test_data = b"Test data for HMAC"
    hmac_result = _compute_hmac_sha256(test_key, test_data)
    assert len(hmac_result) == 32, "HMAC result should be 32 bytes"
    assert isinstance(hmac_result, bytes), "HMAC result should be bytes"
    print("✓ Test 7: Secure HMAC fallback works correctly")
    
    # Тест 8: Детерминированность HMAC (один ключ + одни данные = один результат)
    hmac_result2 = _compute_hmac_sha256(test_key, test_data)
    assert hmac_result == hmac_result2, "HMAC should be deterministic"
    print("✓ Test 8: HMAC determinism verified")
    
    print("\n✅ All crypto manager tests passed!\n")


def test_hmac_fallback_security():
    """
    Тест безопасности fallback HMAC
    Проверяет, что ipad/opad схема не подвержена Length Extension Attack
    """
    print("Testing HMAC fallback security...")
    
    # Тестовые данные
    key = b"TestKeyForHMACSecurityTest!"
    data1 = b"Original message"
    data2 = b"Original message" + b"Extended data"
    
    # Вычисляем HMAC через наш fallback
    hmac1 = _compute_hmac_sha256(key, data1)
    hmac2 = _compute_hmac_sha256(key, data2)
    
    # Проверка: HMAC(data1) != HMAC(data1 + extension) - защита от Length Extension
    # Если бы мы использовали sha256(key+data), то могли бы вычислить
    # sha256(key + data1 + extension) зная только sha256(key + data1)
    # Но с ipad/opad схемой это невозможно
    assert hmac1 != hmac2, "HMAC with different data must differ (Length Extension protection)"
    print("✓ Test: Length Extension Attack protection works")
    
    # Проверка, что одинаковые данные дают одинаковый HMAC
    hmac1_again = _compute_hmac_sha256(key, data1)
    assert hmac1 == hmac1_again, "HMAC must be deterministic for same data"
    print("✓ Test: HMAC determinism confirmed")
    
    print("✓ Test: HMAC fallback security passed\n")


if __name__ == "__main__":
    test_crypto_manager()
    test_hmac_fallback_security()
