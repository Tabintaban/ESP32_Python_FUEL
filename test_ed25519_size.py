"""
Тест границы Ed25519 на ESP32.
Проверяет, при каком размере сообщения verify ломается.
"""

from cryptography.hazmat.primitives.asymmetric import ed25519

sk = ed25519.Ed25519PrivateKey.generate()
pk = sk.public_key()

print("Testing Ed25519 message size limits...")
print("Size | Sign | Verify")
print("-----|------|-------")

sizes = [10, 32, 64, 96, 100, 110, 120, 128, 200, 350, 500]

for size in sizes:
    msg = b'a' * size
    try:
        sig = sk.sign(msg)
        try:
            pk.verify(sig, msg)
            print("%4d | OK   | OK" % size)
        except Exception as e:
            print("%4d | OK   | FAIL (%s)" % (size, type(e).__name__))
    except Exception as e:
        print("%4d | FAIL | - (%s)" % (size, type(e).__name__))

print("Done.")