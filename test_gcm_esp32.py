"""
NIST-тесты для AES-256-GCM на ESP32.
Модуль gcm — C-модуль на mbedTLS.
"""

import gcm


# NIST SP 800-38D, Test Case 13 (AES-256)
TC13 = {
    'name': 'TC13',
    'key': bytes.fromhex('00' * 32),
    'iv':  bytes.fromhex('00' * 12),
    'aad': b'',
    'pt':  b'',
    'ct':  b'',
    'tag': bytes.fromhex('530f8afbc74536b9a963b4f1c4cb738b'),
}

# NIST SP 800-38D, Test Case 14 (AES-256)
TC14 = {
    'name': 'TC14',
    'key': bytes.fromhex('00' * 32),
    'iv':  bytes.fromhex('00' * 12),
    'aad': b'',
    'pt':  bytes.fromhex('00' * 16),
    'ct':  bytes.fromhex('cea7403d4d606b6e074ec5d3baf39d18'),
    'tag': bytes.fromhex('d0d1c8a799996bf0265b98b5d48ab919'),
}

# NIST SP 800-38D, Test Case 15 (AES-256)
TC15 = {
    'name': 'TC15',
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
    print("=== %s ===" % tc['name'])
    try:
        ct, tag = gcm.encrypt(tc['key'], tc['iv'], tc['pt'], tc['aad'])
        ok_ct  = (ct  == tc['ct'])
        ok_tag = (tag == tc['tag'])
        print("  CT:  %s" % ('OK' if ok_ct  else 'FAIL'))
        print("  Tag: %s" % ('OK' if ok_tag else 'FAIL'))
        pt2 = gcm.decrypt(tc['key'], tc['iv'], ct, tag, tc['aad'])
        ok_dec = (pt2 == tc['pt'])
        print("  Decrypt: %s" % ('OK' if ok_dec else 'FAIL'))
        return ok_ct and ok_tag and ok_dec
    except Exception as e:
        print("  [ERROR] %s: %s" % (type(e).__name__, e))
        return False


def main():
    print("NIST SP 800-38D tests on ESP32")
    results = [run_test(tc) for tc in [TC13, TC14, TC15]]
    print("ИТОГ: %d/3 тестов прошло" % sum(results))


main()