"""
AES-256-GCM implementation on pure Python over ucryptolib.aes (CTR mode).

TUR55 раздел 4: AES-256-GCM для шифрования скрипта.

GCM = CTR + GHASH + специальная обработка nonce/tag.
ucryptolib не имеет GCM, поэтому CTR берём оттуда (аппаратное ускорение
на ESP32), а GHASH пишем на чистом Python.

ЭТАП: Шаг 3.1.2.1 — всё, кроме _ghash.
_ghash пока заглушка — тесты упадут по тегу. Это ожидаемо.
"""

import struct

# Пытаемся импортировать ucryptolib (MicroPython/ESP32)
try:
    from ucryptolib import aes as _u_aes
    _HAS_UCRYPTOLIB = True
except ImportError:
    _HAS_UCRYPTOLIB = False

# Fallback для CPython: используем cryptography или чистый Python
if not _HAS_UCRYPTOLIB:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        _HAS_CRYPTOGRAPHY = True
    except ImportError:
        _HAS_CRYPTOGRAPHY = False
else:
    _HAS_CRYPTOGRAPHY = False


def _to_bytes(x):
    """Приведение к bytes, если пришла str."""
    if isinstance(x, str):
        return x.encode('utf-8')
    return bytes(x)


class GCM:
    """
    AES-256-GCM.

    Использование:
        gcm = GCM(key32)
        iv, ct, tag = gcm.encrypt(plaintext, aad)
        pt = gcm.decrypt(iv, ct, tag, aad)

    Формат IV: 12 байт (стандарт GCM).
    """

    BLOCK_SIZE = 16

    def __init__(self, key):
        """
        Args:
            key: 32 байта (AES-256).
        """
        if len(key) != 32:
            raise ValueError("GCM key must be 32 bytes (AES-256)")
        self.key = bytes(key)
        # H = AES_K(0^128) — для GHASH. Вычисляем сразу.
        self._h = self._compute_h()
        # Предвычисленная таблица для табличного GHASH (4-бит).
        # 16 значений: H * x для x = 0..15.
        self._m = self._precompute_table(self._h)

    # ------------------------------------------------------------------ #
    # Публичный API
    # ------------------------------------------------------------------ #

    def encrypt(self, plaintext, aad=b'', iv=None):
        """
        Шифрование.

        Args:
            plaintext: bytes для шифрования.
            aad: associated authenticated data (по умолчанию пусто).
            iv: 12-байтный nonce. Если None — генерируется случайно.
                ВАЖНО: для TUR55 IV передаётся вместе с ciphertext.

        Returns:
            (iv, ciphertext, tag): iv 12 байт, ciphertext той же длины,
                                    что plaintext, tag 16 байт.
        """
        plaintext = _to_bytes(plaintext)
        aad = _to_bytes(aad)

        if iv is None:
            iv = self._random_iv()
        else:
            iv = _to_bytes(iv)
            if len(iv) != 12:
                raise ValueError("GCM: IV must be 12 bytes")

        # J0 = IV || 0x00000001
        j0 = iv + b'\x00\x00\x00\x01'

        # C = GCTR(inc32(J0), plaintext)
        ciphertext = self._gctr(self._inc32(j0), plaintext)

        # S = GHASH(H, AAD, C)
        s = self._ghash_with_lengths(self._h, aad, ciphertext)

        # T = MSB_128(GCTR(J0, S))
        tag = self._gctr(j0, s)

        return iv, ciphertext, tag

    def decrypt(self, iv, ciphertext, tag, aad=b''):
        """
        Расшифровка с проверкой тега.

        Args:
            iv: 12 байт.
            ciphertext: bytes.
            tag: 16 байт.
            aad: associated authenticated data.

        Returns:
            plaintext (bytes).

        Raises:
            ValueError: если тег не совпал (данные подменены).
        """
        iv = _to_bytes(iv)
        ciphertext = _to_bytes(ciphertext)
        tag = _to_bytes(tag)
        aad = _to_bytes(aad)

        if len(iv) != 12:
            raise ValueError("GCM: IV must be 12 bytes")
        if len(tag) != 16:
            raise ValueError("GCM: tag must be 16 bytes")

        # J0 = IV || 0x00000001
        j0 = iv + b'\x00\x00\x00\x01'

        # S = GHASH(H, AAD, C)
        s = self._ghash_with_lengths(self._h, aad, ciphertext)

        # T' = MSB_128(GCTR(J0, S))
        expected_tag = self._gctr(j0, s)

        # Constant-time сравнение
        if not self._constant_time_eq(expected_tag, tag):
            raise ValueError("GCM: authentication failed (tag mismatch)")

        # P = GCTR(inc32(J0), C)
        plaintext = self._gctr(self._inc32(j0), ciphertext)

        return plaintext

    # ------------------------------------------------------------------ #
    # Внутренние примитивы
    # ------------------------------------------------------------------ #

    def _compute_h(self):
        """H = AES_K(0^128) — один блок нулей, зашифрованный ключом."""
        zero_block = b'\x00' * 16
        return self._aes_block_encrypt(zero_block)

    def _aes_block_encrypt(self, block):
        """
        Один блок AES-256 (16 байт -> 16 байт).
        Используется для вычисления H.
        """
        if len(block) != 16:
            raise ValueError("AES block must be 16 bytes")
        if _HAS_UCRYPTOLIB:
            # ECB-режим: mode=1
            cipher = _u_aes(self.key, 1)
            return cipher.encrypt(block)
        elif _HAS_CRYPTOGRAPHY:
            cipher = Cipher(algorithms.AES(self.key), modes.ECB())
            enc = cipher.encryptor()
            return enc.update(block) + enc.finalize()
        else:
            raise RuntimeError(
                "Нет доступного AES: ни ucryptolib, ни cryptography. "
                "Установи: py -m pip install cryptography"
            )

    def _gctr(self, icb, data):
        """
        GCTR(K, ICB, X) — CTR-режим с начальным counter block ICB.

        ВХОД:  icb — 16 байт (initial counter block)
               data — bytes
        ВЫХОД: bytes той же длины
        """
        if len(icb) != 16:
            raise ValueError("GCTR: ICB must be 16 bytes")
        if len(data) == 0:
            return b''

        if _HAS_UCRYPTOLIB:
            # CTR mode = 2, IV = icb (16 байт)
            cipher = _u_aes(self.key, 2, icb)
            return cipher.encrypt(data)
        elif _HAS_CRYPTOGRAPHY:
            cipher = Cipher(algorithms.AES(self.key), modes.CTR(icb))
            enc = cipher.encryptor()
            return enc.update(data) + enc.finalize()
        else:
            raise RuntimeError(
                "Нет доступного AES: ни ucryptolib, ни cryptography."
            )

    @staticmethod
    def _inc32(block):
        """
        inc32(X) — инкремент последних 32 бит X по модулю 2^32.
        Первые 12 байт не меняются.
        """
        if len(block) != 16:
            raise ValueError("inc32: block must be 16 bytes")
        prefix = block[:12]
        counter = struct.unpack('>I', block[12:])[0]
        counter = (counter + 1) & 0xFFFFFFFF
        return prefix + struct.pack('>I', counter)

    @staticmethod
    def _random_iv():
        """Генерация 12-байтного IV."""
        try:
            import urandom
            return urandom.urandom(12)
        except ImportError:
            import os
            return os.urandom(12)

    @staticmethod
    def _constant_time_eq(a, b):
        """Сравнение за постоянное время (защита от timing-атак)."""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        return result == 0

    def _precompute_table(self, h):
        """
        Предвычисление таблицы для табличного GHASH (4-бит).

        Таблица M[0..15]: M[i] = H * i (умножение в GF(2^128)).
        M[0] = 0
        M[1] = H
        M[2] = H * 2
        ...
        M[15] = H * 15

        Вычисляется через побитовый _gf_mul — один раз при создании GCM.
        """
        h_int = int.from_bytes(h, 'big')
        table = [0] * 16
        for i in range(16):
            table[i] = self._gf_mul(i, h_int)
        return table

    @staticmethod
    def _gf_mul_by_2(x):
        """
        Умножение 128-битного числа на x в GF(2^128).
        Используется для построения таблицы.
        """
        R = 0xE1000000000000000000000000000000
        if x & 1:
            return (x >> 1) ^ R
        return x >> 1

    @staticmethod
    def _gf_mul_by_4(x):
        """Умножение на x^2 (два раза на x)."""
        return GCM._gf_mul_by_2(GCM._gf_mul_by_2(x))

    @staticmethod
    def _gf_mul_by_8(x):
        """Умножение на x^3 (три раза на x)."""
        return GCM._gf_mul_by_2(GCM._gf_mul_by_4(x))

    # ------------------------------------------------------------------ #
    # GHASH — ядро GCM (ЗАГЛУШКА — реализуем в Шаге 3.1.2.2)
    # ------------------------------------------------------------------ #

    def _ghash(self, h, data):
        """
        GHASH(H, data) — побитовая версия.

        S = 0^128
        для каждого 16-байтного блока X_i:
            S = (S XOR X_i) * H
        вернуть S
        """
        if len(data) % 16 != 0:
            raise ValueError("GHASH: data length must be multiple of 16")

        h_int = int.from_bytes(h, 'big')
        s_int = 0

        for i in range(0, len(data), 16):
            block = data[i:i+16]
            x_int = int.from_bytes(block, 'big')
            s_int = self._gf_mul(s_int ^ x_int, h_int)

        return s_int.to_bytes(16, 'big')
    
    @staticmethod
    def _gf_mul(a, b):
        """
        Умножение двух 128-битных чисел в GF(2^128)
        с полиномом x^128 + x^7 + x^2 + x + 1.

        NIST SP 800-38D, Algorithm 1:
          Z = 0
          V = X (= a)
          for i = 0 to 127:
              if X_i == 1:        # X_i — i-й бит X, от СТАРШЕГО
                  Z ^= V
              if V_127 == 0:      # V_127 — СТАРШИЙ бит V
                  V >>= 1
              else:
                  V = (V >> 1) ^ R
          return Z

        R = 0xE1 << 120 = 0xE1000000000000000000000000000000
        """
        R = 0xE1000000000000000000000000000000

        z = 0
        v = b  # V = H (второй аргумент)

        for i in range(128):
            # Проверяем i-й бит X от СТАРШЕГО.
            # i=0 — старший бит (бит 127), i=127 — младший (бит 0).
            bit = (a >> (127 - i)) & 1
            if bit:
                z ^= v

            # V = V >> 1, с редукцией если вышел старший бит
            if v & 1:
                # Младший бит V выходит при сдвиге вправо,
                # НО редукция в GCM применяется когда выходит СТАРШИЙ бит.
                # Для этого представления: если МЛАДШИЙ бит V = 1,
                # то V >> 1 и XOR с R.
                # (Это потому что в GCM байты идут в обратном порядке.)
                v = (v >> 1) ^ R
            else:
                v >>= 1

        return z
    
    def _ghash_with_lengths(self, h, aad, ciphertext):
        """
        GHASH с правильной обработкой AAD и ciphertext:
        S = GHASH(H, AAD || pad || C || pad || len(AAD)*8 || len(C)*8)

        ЗАГЛУШКА — использует _ghash (который пока возвращает нули).
        После реализации _ghash этот метод заработает.
        """
        # Паддинг AAD до кратности 16
        aad_padded = aad + b'\x00' * ((16 - len(aad) % 16) % 16)
        # Паддинг ciphertext до кратности 16
        ct_padded = ciphertext + b'\x00' * ((16 - len(ciphertext) % 16) % 16)
        # Длина в битах
        lengths = struct.pack('>QQ', len(aad) * 8, len(ciphertext) * 8)

        data = aad_padded + ct_padded + lengths
        return self._ghash(h, data)