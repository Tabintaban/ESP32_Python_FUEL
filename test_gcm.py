"""
NIST-векторы для AES-256-GCM (из NIST SP 800-38D, Test Case 13-16).

Эти тесты — ЭТАЛОН. Если GCM не совпадает с ними — он НЕПРАВИЛЬНЫЙ.

На Шаге 3.1.1 тесты будут падать с NotImplementedError —
это ожидаемо, потому что GCM ещё не реализован.
"""

import sys
sys.path.insert(0, '.')

from gcm import GCM


# NIST SP 800-38D, Test Case 13 (AES-256)
# Key = 0^256
# IV  = 0^96
# PT  = пусто
# AAD = пусто
# CT  = пусто
# Tag = 530f8afbc74536b9a963b4f1c4cb738b
NIST_TC13 = {
    'name': 'TC13 (AES-256, empty PT/AAD)',
    'key': bytes.fromhex('00' * 32),
    'iv':  bytes.fromhex('00' * 12),
    'aad': b'',
    'pt':  b'',
    'ct':  b'',
    'tag': bytes.fromhex('530f8afbc74536b9a963b4f1c4cb738b'),
}

# NIST SP 800-38D, Test Case 14 (AES-256)
# Key = 0^256
# IV  = 0^96
# PT  = 0^128
# AAD = пусто
# CT  = cea7403d4d606b6e074ec5d3baf39d18
# Tag = d0d1c8a799996bf0265b98b5d48ab919
NIST_TC14 = {
    'name': 'TC14 (AES-256, 128-bit PT, empty AAD)',
    'key': bytes.fromhex('00' * 32),
    'iv':  bytes.fromhex('00' * 12),
    'aad': b'',
    'pt':  bytes.fromhex('00' * 16),
    'ct':  bytes.fromhex('cea7403d4d606b6e074ec5d3baf39d18'),
    'tag': bytes.fromhex('d0d1c8a799996bf0265b98b5d48ab919'),
}

# NIST SP 800-38D, Test Case 15 (AES-256)
# Key = feffe9928665731c6d6a8f9467308308feffe9928665731c6d6a8f9467308308
# IV  = cafebabefacedbaddecaf888
# PT  = d9313225f88406e5a55909c5aff5269a
#       86a7a9531534f7da2e4c303d8a318a72
#       1c3c0c95956809532fcf0e2449a6b525
#       b16aedf5aa0de657ba637b39
# AAD = feedfacedeadbeeffeedfacedeadbeefabaddad2
# CT  = 522dc1f099567d07f47f37a32a84427d
#       643a8cdcbfe5c0c97598a2bd2555d1aa
#       8cb08e48590dbb3da7b08b1056828838
#       c5f61e6393ba7a0abcc9f662
# Tag = 76fc6ece0f4e1768cddf8853bb2d551b
NIST_TC15 = {
    'name': 'TC15 (AES-256, 408-bit PT, 160-bit AAD)',
    'key': bytes.fromhex(
        'feffe9928665731c6d6a8f9467308308'
        'feffe9928665731c6d6a8f9467308308'
    ),
    'iv':  bytes.fromhex('cafebabefacedbaddecaf888'),
    'aad': bytes.fromhex('feedfacedeadbeeffeedfacedeadbeefabaddad2'),
    'pt':  bytes.fromhex(
        'd9313225f88406e5a55909c5aff5269a'
        '86a7a9531534f7da2e4c303d8a318a72'
        '1c3c0c95956809532fcf0e2449a6b525'
        'b16aedf5aa0de657ba637b39'
    ),
    'ct':  bytes.fromhex(
        '522dc1f099567d07f47f37a32a84427d'
        '643a8cdcbfe5c0c97598a2bd2555d1aa'
        '8cb08e48590dbb3da7b08b1056828838'
        'c5f61e6393ba7a0abcc9f662'
    ),
    'tag': bytes.fromhex('76fc6ece0f4e1768cddf8853bb2d551b'),
}


def run_test(tc):
    """
    Прогон одного теста с ЯВНЫМ IV из NIST-вектора.
    """
    print("\n=== %s ===" % tc['name'])
    try:
        gcm = GCM(tc['key'])

        # ВАЖНО: передаём IV из NIST-вектора, а не случайный
        iv, ct, tag = gcm.encrypt(tc['pt'], tc['aad'], iv=tc['iv'])

        ok_iv  = (iv  == tc['iv'])
        ok_ct  = (ct  == tc['ct'])
        ok_tag = (tag == tc['tag'])

        print("  IV:  %s -> %s" % (iv.hex(),  'OK' if ok_iv  else 'FAIL'))
        print("  CT:  %s" % ct.hex())
        print("       ожидалось %s -> %s" % (tc['ct'].hex(),  'OK' if ok_ct  else 'FAIL'))
        print("  Tag: %s" % tag.hex())
        print("       ожидалось %s -> %s" % (tc['tag'].hex(), 'OK' if ok_tag else 'FAIL'))

        # Проверка расшифровки (передаём IV, ct, tag)
        pt2 = gcm.decrypt(iv, ct, tag, tc['aad'])
        print("  Decrypt: %s" % ('OK' if pt2 == tc['pt'] else 'FAIL'))

        return ok_iv and ok_ct and ok_tag and pt2 == tc['pt']

    except NotImplementedError as e:
        print("  [ОЖИДАЕМО] %s" % e)
        return False
    except Exception as e:
        print("  [ОШИБКА] %s: %s" % (type(e).__name__, e))
        return False


def main():
    print("=" * 60)
    print("ПРОВЕРКА _gf_mul (NIST SP 800-38D, Test Case 2)")
    print("=" * 60)
    h = bytes.fromhex('66e94bd4ef8a2c3b884cfa59ca342b2e')
    x = bytes.fromhex('0388dace60b6a392f328c2b971b2fe78')
    expected = '5e2ec746917062882c85b0685353deb7'

    h_int = int.from_bytes(h, 'big')
    x_int = int.from_bytes(x, 'big')
    result_int = GCM._gf_mul(x_int, h_int)
    result = result_int.to_bytes(16, 'big')

    print("H:        %s" % h.hex())
    print("X:        %s" % x.hex())
    print("Ожидалось: %s" % expected)
    print("Получено:  %s" % result.hex())
    print("Результат: %s" % ('OK' if result.hex() == expected else 'FAIL'))
    print()

    print("=" * 60)
    print("NIST SP 800-38D тесты для AES-256-GCM")
    print("=" * 60)
    print("(На Шаге 3.1.1 ожидаем NotImplementedError — GCM ещё не готов)")
    # ... остальной код
    
    tests = [NIST_TC13, NIST_TC14, NIST_TC15]
    results = [run_test(tc) for tc in tests]

    print("\n" + "=" * 60)
    print("ИТОГ: %d/%d тестов прошло" % (sum(results), len(results)))

if __name__ == '__main__':
    main()