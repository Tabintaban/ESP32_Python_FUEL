# NEXT SESSION — статус и план

## Дата последней сессии: 2026-10-10

## Что сделано

### Инфраструктура
- ✅ WSL Ubuntu 22.04
- ✅ Python 3.10.12
- ✅ ESP-IDF **v5.3.2** (v5.1.2 не подошёл — требует >= 5.3.0)
- ✅ MicroPython клонирован
- ✅ `mpy-cross` собран

### GCM-модуль для ESP32
- ✅ Создан `~/cmodules/gcm/modgcm.c` (C-модуль на mbedTLS)
- ✅ Создан `~/cmodules/gcm/micropython.cmake`
- ✅ Использованы **правильные** макросы:
  - `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN` (не `_4`/`_5`)
  - Только `#include "py/runtime.h"` и `"py/mphal.h"`
- ✅ **Сборка успешна** — `micropython.bin` (1.7 МБ)
- ✅ Прошивка **залита**

### Проблема
- ❌ **GCM-прошивка не загружается** — REPL не отвечает
- ✅ Откат к v1.29.0 — **работает**

### Диагноз
Модуль `gcm` **падает при старте MicroPython**.
Возможные причины:
- Ошибка в C-коде
- Конфликт с mbedTLS
- Проблема с памятью
- Неверный API

## План на следующую сессию

### Отладка GCM-модуля

1. **Упростить модуль** — оставить только `encrypt`, без `decrypt`
2. **Убрать mbedTLS** временно — проверить, что модуль **регистрируется** без него
3. **Добавить логи** через `mp_printf` — увидеть, где падает
4. **Проверить инициализацию** mbedTLS
5. **Постепенно** добавлять функциональность

### Полезные команды

Размер прошивки:

    ls -la ~/micropython/ports/esp32/build-ESP32_GENERIC/micropython.bin

Монитор порта (Windows):

    py -m serial.tools.miniterm COM3 115200

Пересборка:

    cd ~/micropython/ports/esp32
    rm -rf build-ESP32_GENERIC
    make BOARD=ESP32_GENERIC USER_C_MODULES=/home/tavintavan/cmodules/gcm/micropython.cmake

## Статус TUR55/Bronze

| Требование | Статус |
|---|---|
| Раздел 3.4 — структура пакета | ❌ |
| Раздел 4 — AES-256-GCM | ⏳ Собран, но не работает |
| Раздел 4 — Ed25519/ECDSA | ❌ |
| Раздел 4 — ECIES/RSA-OAEP | ❌ |
| Раздел 4 — SHA3-256/Blake2s | ❌ |
| Раздел 4 — eFuse | ❌ |
| Раздел 5 — проверка expires | ❌ |
| Раздел 6 — whitelist модулей | ✅ |