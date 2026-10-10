# NEXT SESSION — статус и план

## Дата последней сессии: 2026-10-10

## 🎉 ГЛАВНАЯ ПОБЕДА

**AES-256-GCM работает на ESP32 и соответствует NIST SP 800-38D (3/3).**

## Рабочая комбинация (проверено)

| Компонент | Версия |
|---|---|
| MicroPython | **v1.24.1** |
| ESP-IDF | **v5.2.2** |
| ESP32 | ESP32-D0WDQ6-V3 (WROOM) |

**ESP-IDF v5.1.2 и v5.3.2 — НЕ подходят.**

## Что сделано

### Решена проблема boot loop
**Причина:** заливали только `micropython.bin` на `0x1000`.
**Решение:** заливать **три файла** по **трём адресам**:
- `bootloader.bin` → `0x1000`
- `partition-table.bin` → `0x8000`
- `micropython.bin` → `0x10000`

### GCM-модуль
- ✅ `~/cmodules/gcm/modgcm.c` — C-модуль на mbedTLS
- ✅ `~/cmodules/gcm/micropython.cmake`
- ✅ `gcm.encrypt(key, iv, pt, aad)` → `(ct, tag)`
- ✅ `gcm.decrypt(key, iv, ct, tag, aad)` → `pt`
- ✅ NIST-тесты на ESP32: **3/3**

### Тесты
- ✅ `test_gcm_esp32.py` залит на ESP32
- ✅ Round-trip: `b'hello world'` → encrypt → decrypt → `b'hello world'`
- ✅ NIST TC13, TC14, TC15 — все OK

### Инструкция
- ✅ `BUILD_GCM_FIRMWARE.md` — полная инструкция сборки

## Что осталось для TUR55/Bronze

| Требование | Статус |
|---|---|
| Раздел 3.4 — структура пакета | ❌ |
| Раздел 4 — AES-256-GCM | ✅ **Готово** |
| Раздел 4 — Ed25519/ECDSA | ❌ |
| Раздел 4 — ECIES/RSA-OAEP | ❌ |
| Раздел 4 — SHA3-256/Blake2s | ❌ |
| Раздел 4 — eFuse | ❌ |
| Раздел 5 — проверка expires | ❌ |
| Раздел 6 — whitelist модулей | ✅ |

## План следующей сессии

**Приоритет 1 — Формат пакета TUR55 (раздел 3.4)**

Структура:
[HEADER: TUR55v1]
[ENCRYPTED_SESSION_KEY]
[ENCRYPTED_SCRIPT] (AES-256-GCM)
[SIGNATURE] (Ed25519)


**Приоритет 2 — Ed25519 / ECDSA**

mbedTLS поддерживает ECDSA. Можно использовать **mbedtls_ecdsa_*** в C-модуле.

**Приоритет 3 — SHA3-256 / Blake2s**

mbedTLS поддерживает **SHA3-256**. Blake2s — через отдельную реализацию.

## Полезные команды

### Собрать прошивку

```bash
. ~/esp/esp-idf-v5.2.2/export.sh
cd ~/micropython/ports/esp32
rm -rf build-ESP32_GENERIC
make BOARD=ESP32_GENERIC USER_C_MODULES=/home/tavintavan/cmodules/gcm/micropython.cmake
```

### Залить

```bash
# download mode: BOOT + EN
py -m esptool --chip esp32 --port COM3 erase-flash
# download mode снова
py -m esptool --chip esp32 --port COM3 --baud 460800 write-flash --flash-mode dio --flash-size 4MB --flash-freq 40m -z 0x1000 "bootloader.bin" 0x8000 "partition-table.bin" 0x10000 "micropython.bin"
```
### Проверить

```bash
py -m serial.tools.miniterm COM3 115200
```
### Ссылки
- BUILD_GCM_FIRMWARE.md — полная инструкция
- NIST SP 800-38D: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf
- mbedTLS ECDSA: https://mbed-tls.readthedocs.io/


## Шаг 2 — коммит

**PowerShell:**

```powershell
cd C:\Users\user\documents\projects\esp32_python_fuel
git add NEXT_SESSION.md
git commit -m "GCM works on ESP32 - NIST 3/3 passed"
git push
```
