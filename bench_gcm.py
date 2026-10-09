"""
Замер производительности AES-256-GCM на чистом Python.

Цель: понять, сколько времени занимает encrypt/decrypt для пакетов
размером 1, 5, 10, 20 KB. На CPython. Потом сравним с ESP32.

Важно: GHASH сейчас ПОБИТОВЫЙ (самый медленный вариант).
Если результаты плохие — перейдём на табличный GHASH.
"""

import sys
import time
import os

sys.path.insert(0, '.')

from gcm import GCM


def bench_size(size_kb, iterations=5):
    """
    Замер для одного размера.
    Возвращает (avg_encrypt_ms, avg_decrypt_ms, throughput_kbps).
    """
    size_bytes = size_kb * 1024

    # Тестовые данные
    key = os.urandom(32)
    iv  = os.urandom(12)
    pt  = os.urandom(size_bytes)
    aad = b'TUR55-packet-header'

    gcm = GCM(key)

    # Прогрев (первый вызов может быть медленнее)
    gcm.encrypt(pt, aad, iv=iv)

    # Замер encrypt
    t0 = time.perf_counter()
    for _ in range(iterations):
        iv_out, ct, tag = gcm.encrypt(pt, aad, iv=iv)
    t1 = time.perf_counter()
    avg_encrypt_ms = (t1 - t0) / iterations * 1000

    # Замер decrypt
    t0 = time.perf_counter()
    for _ in range(iterations):
        pt2 = gcm.decrypt(iv_out, ct, tag, aad)
    t1 = time.perf_counter()
    avg_decrypt_ms = (t1 - t0) / iterations * 1000

    # Проверка корректности
    assert pt2 == pt, "ОШИБКА: decrypt вернул не тот plaintext!"

    # Пропускная способность (KB/сек)
    throughput = size_kb / (avg_encrypt_ms / 1000)

    return avg_encrypt_ms, avg_decrypt_ms, throughput


def main():
    print("=" * 70)
    print("BENCHMARK: AES-256-GCM на чистом Python (CPython)")
    print("=" * 70)
    print("GHASH: побитовый (самый медленный вариант)")
    print("Замер: среднее из 5 итераций")
    print()

    sizes = [1, 5, 10, 20]

    print("%-8s | %-15s | %-15s | %-12s" % (
        "Размер", "Encrypt (мс)", "Decrypt (мс)", "KB/сек"))
    print("-" * 70)

    results = []
    for kb in sizes:
        enc, dec, thr = bench_size(kb, iterations=5)
        results.append((kb, enc, dec, thr))
        print("%-6d KB | %-15.1f | %-15.1f | %-12.0f" % (kb, enc, dec, thr))

    print()
    print("=" * 70)
    print("АНАЛИЗ")
    print("=" * 70)

    # Оценка для TUR55: пакет ~10 KB, лимит 500 мс на весь цикл
    print()
    print("TUR55 требует: <500 мс на весь цикл (загрузка+дешифровка+выполнение).")
    print()

    for kb, enc, dec, thr in results:
        total = enc + dec
        status = "OK" if total < 100 else "МЕДЛЕННО"
        print("  %2d KB: encrypt+decrypt = %.1f мс (%s)" % (kb, total, status))

    print()
    print("ВАЖНО:")
    print("  - Это CPython. На ESP32 будет в 10-50 раз медленнее.")
    print("  - Если 10 KB на CPython = 50 мс, на ESP32 = 500-2500 мс.")
    print("  - Это МОЖЕТ не уложиться в лимит TUR55.")
    print()
    print("Если результаты неприемлемы — переходим на табличный GHASH")
    print("(Вариант B, в 2-4 раза быстрее).")


if __name__ == '__main__':
    main()