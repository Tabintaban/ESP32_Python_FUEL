"""
GCM adapter — единый интерфейс для CPython и ESP32.

На CPython: использует gcm.py (класс GCM).
На ESP32:   использует C-модуль gcm (функции encrypt/decrypt).
"""

try:
    # ESP32: C-модуль
    import gcm as _c_gcm
    if hasattr(_c_gcm, 'encrypt'):
        # C-модуль
        def encrypt(key, iv, pt, aad):
            return _c_gcm.encrypt(key, iv, pt, aad)

        def decrypt(key, iv, ct, tag, aad):
            return _c_gcm.decrypt(key, iv, ct, tag, aad)

    else:
        raise ImportError("gcm is not C-module")

except (ImportError, AttributeError):
    # CPython: Python-версия
    from gcm import GCM

    def encrypt(key, iv, pt, aad):
        g = GCM(key)
        iv_out, ct, tag = g.encrypt(pt, aad, iv=iv)
        return ct, tag

    def decrypt(key, iv, ct, tag, aad):
        g = GCM(key)
        return g.decrypt(iv, ct, tag, aad)