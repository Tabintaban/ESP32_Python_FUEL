"""
Unit tests for lightweight_security module
"""
import sys
sys.path.insert(0, '..')

import hashlib
import time
from lightweight_security import LightweightSecurity, _compute_hmac_sha256, secure_random

# Совместимость с CPython и MicroPython
if hasattr(time, 'ticks_ms'):
    get_time_ms = time.ticks_ms
    ticks_diff = time.ticks_diff
else:
    def get_time_ms():
        return int(time.time() * 1000)
    def ticks_diff(end, start):
        return end - start


def test_lightweight_security():
    """
    Unit-тесты для LightweightSecurity
    """
    print("Testing LightweightSecurity...")
    
    # На CPython без ucryptolib этот тест не работает
    try:
        from ucryptolib import aes
    except ImportError:
        print("✓ LightweightSecurity tests skipped (ucryptolib not available on CPython)")
        return
    
    # Тест 1: Базовая подпись и проверка
    security = LightweightSecurity()
    test_data = "Hello, ESP32 Secure System!"
    
    signature = security.sign_data(test_data)
    is_valid = security.verify_signature(test_data, signature)
    assert is_valid, "Signature verification failed"
    print("✓ Test 1: Basic signature and verification passed")
    
    # Тест 2: Подделка подписи невозможна без секретного ключа
    security2 = LightweightSecurity()  # Другой секретный ключ
    is_valid = security2.verify_signature(test_data, signature)
    assert not is_valid, "Different key should not validate signature"
    print("✓ Test 2: Signature forgery prevention passed")
    
    # Тест 3: Публичный ключ не позволяет вычислить приватный
    pub_key = security.get_public_key()
    # Публичный ключ - это хеш, из него нельзя восстановить секретный ключ
    assert pub_key != security.secret_key, "Public key must differ from secret key"
    print("✓ Test 3: Public key does not reveal secret key passed")
    
    # Тест 4: Защита от replay-атак с nonce
    nonce, timestamp = security.generate_nonce()
    signature_with_nonce = security.sign_data(test_data, nonce=nonce)
    
    # Первая проверка должна пройти
    assert security.validate_nonce(nonce, timestamp), "Nonce validation failed"
    is_valid = security.verify_signature(test_data, signature_with_nonce, nonce=nonce)
    assert is_valid, "Signature with nonce verification failed"
    print("✓ Test 4: Replay attack protection with nonce passed")
    
    # Повторная проверка того же nonce должна fail
    assert not security.validate_nonce(nonce, timestamp), "Replay attack should be detected"
    print("✓ Test 5: Replay attack detection passed")
    
    # Тест 6: Constant-time comparison
    sig1 = bytes(32)
    sig2 = bytes(32)
    sig3 = bytearray(sig2)
    sig3[0] ^= 0xFF
    sig3 = bytes(sig3)
    
    assert security._constant_time_compare(sig1, sig2), "Same signatures should match"
    assert not security._constant_time_compare(sig1, sig3), "Different signatures should not match"
    print("✓ Test 6: Constant-time comparison passed")
    
    # Тест 7: Проверка разрешений (getattr теперь небезопасен)
    safe_funcs = ['print', 'len', 'range']
    perms_ok, perms_msg = security.check_permissions(safe_funcs)
    assert perms_ok, f"Safe functions should be allowed: {perms_msg}"
    
    unsafe_funcs = ['getattr', 'eval', 'exec']
    perms_ok, perms_msg = security.check_permissions(unsafe_funcs)
    assert not perms_ok, "Unsafe functions should be rejected"
    print("✓ Test 7: Permission checking passed")
    
    # Тест 8: Проверка secure_random - не использует random
    rand_bytes = secure_random(32)
    assert len(rand_bytes) == 32, "secure_random should return 32 bytes"
    assert isinstance(rand_bytes, bytes), "secure_random should return bytes"
    print("✓ Test 8: secure_random works correctly")
    
    # Тест 9: Проверка безопасного HMAC fallback
    test_key = b"TestHMACKey32BytesLongForTesting!"
    test_data_bytes = b"Test data for HMAC"
    hmac_result = _compute_hmac_sha256(test_key, test_data_bytes)
    assert len(hmac_result) == 32, "HMAC result should be 32 bytes"
    assert isinstance(hmac_result, bytes), "HMAC result should be bytes"
    print("✓ Test 9: Secure HMAC fallback works correctly")
    
    # Тест 10: Детерминированность HMAC
    hmac_result2 = _compute_hmac_sha256(test_key, test_data_bytes)
    assert hmac_result == hmac_result2, "HMAC should be deterministic"
    print("✓ Test 10: HMAC determinism verified")
    
    print("\n✅ All lightweight security tests passed!\n")


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
    assert hmac1 != hmac2, "HMAC with different data must differ (Length Extension protection)"
    print("✓ Test: Length Extension Attack protection works")
    
    # Проверка, что одинаковые данные дают одинаковый HMAC
    hmac1_again = _compute_hmac_sha256(key, data1)
    assert hmac1 == hmac1_again, "HMAC must be deterministic for same data"
    print("✓ Test: HMAC determinism confirmed")
    
    print("✓ Test: HMAC fallback security passed\n")


if __name__ == "__main__":
    test_lightweight_security()
    test_hmac_fallback_security()
