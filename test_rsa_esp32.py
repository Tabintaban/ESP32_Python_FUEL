"""
Тест RSA-OAEP на ESP32.
"""

import json
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateNumbers, RSAPublicNumbers
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes


def load_key():
    f = open('esp32_private_key.json', 'r')
    content = f.read()
    f.close()
    c = json.loads(content)

    n = int.from_bytes(bytes.fromhex(c['n']), 'big')
    e = c['e']
    d = int.from_bytes(bytes.fromhex(c['d']), 'big')
    p = int.from_bytes(bytes.fromhex(c['p']), 'big')
    q = int.from_bytes(bytes.fromhex(c['q']), 'big')
    dmp1 = int.from_bytes(bytes.fromhex(c['dmp1']), 'big')
    dmq1 = int.from_bytes(bytes.fromhex(c['dmq1']), 'big')
    iqmp = int.from_bytes(bytes.fromhex(c['iqmp']), 'big')

    pub = RSAPublicNumbers(e, n)
    priv = RSAPrivateNumbers(p, q, d, dmp1, dmq1, iqmp, pub)
    return priv.private_key()


def main():
    print("=" * 60)
    print("RSA-OAEP test on ESP32")
    print("=" * 60)

    # 1. Загрузка ключа
    print("\n1. Loading key...")
    key = load_key()
    print("   Key OK")

    # 2. Padding
    print("\n2. Setting padding...")
    mgf = padding.MGF1(hashes.SHA256())
    oaep = padding.OAEP(mgf, hashes.SHA256(), None)
    print("   Padding OK")

    # 3. Self-test: encrypt + decrypt
    print("\n3. Self-test (encrypt + decrypt)...")
    try:
        ct = key.public_key().encrypt(b'test', oaep)
        print("   Encrypted OK, ct len:", len(ct))

        pt = key.decrypt(ct, oaep)
        print("   Decrypted:", pt)
    except Exception as e:
        print("   FAIL:", type(e).__name__, str(e))
        return

    # 4. Реальный пакет
    print("\n4. Real packet test...")
    packet = open('test_packet.bin', 'rb').read()
    sk_len = packet[42] * 256 + packet[43]
    enc_sk = packet[44:44+sk_len]
    print("   enc_sk len:", len(enc_sk))

    try:
        session_key = key.decrypt(enc_sk, oaep)
        print("   session_key len:", len(session_key))
        print("   session_key:", session_key.hex())
    except Exception as e:
        print("   FAIL:", type(e).__name__, str(e))
        return

    print("\n" + "=" * 60)
    print("✅ RSA-OAEP WORKS")
    print("=" * 60)


main()