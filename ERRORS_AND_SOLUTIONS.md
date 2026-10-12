## Документ 2 — `ERRORS_AND_SOLUTIONS.md`

**Создай файл** `ERRORS_AND_SOLUTIONS.md` в папке проекта.

**Содержимое:**


# ERRORS_AND_SOLUTIONS — база ошибок ESP32_Python_FUEL

**Назначение:** каталог ошибок, с которыми столкнулись, и их решений.

---

## 1. Boot loop ESP32 (`RTCWDT_RTC_RESET`)

**Симптом:**
```markdown
rst:0x10 (RTCWDT_RTC_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
load:0x3f400020,len:262772
ets Jul 29 2019 12:21:46
... (цикл)
```

**Причина:** заливка **только `micropython.bin`** на `0x1000`.  
**Правильно:** нужно **три файла** по **трём адресам**.

**Решение:**
```powershell
py -m esptool --chip esp32 --port COM3 --baud 460800 write-flash --flash-mode dio --flash-size 4MB --flash-freq 40m -z 0x1000 "bootloader.bin" 0x8000 "partition-table.bin" 0x10000 "micropython.bin"
```

**Адреса:**
- `bootloader.bin` → `0x1000`
- `partition-table.bin` → `0x8000`
- `micropython.bin` → `0x10000`

---

## 2. ESP-IDF несовместим с MicroPython

**Симптом:** ошибка версии IDF при сборке.

**Причина:** MicroPython поддерживает **только определённые версии ESP-IDF**.

**Правильные комбинации:**

| MicroPython | ESP-IDF |
|---|---|
| v1.24.1 | **v5.2.2** ✅ |
| v1.30 (main) | v5.3+ |
| — | v5.1.2 ❌ (не в списке) |
| — | v5.3.2 ❌ (требует v1.30) |

**Решение:** использовать **MicroPython v1.24.1 + ESP-IDF v5.2.2**.

---

## 3. `STATIC` не определён

**Симптом:**
```
error: unknown type name 'STATIC'
```

**Причина:** макрос `STATIC` **удалён** в новых версиях MicroPython.

**Решение:** заменить все `STATIC` на **`static`**:
```bash
sed -i 's/\bSTATIC\b/static/g' file.c
```

---

## 4. `MP_DEFINE_CONST_FUN_OBJ_4` не существует

**Симптом:**
```
error: implicit declaration of function 'MP_DEFINE_CONST_FUN_OBJ_4'
```

**Причина:** макросы `_4` и `_5` **удалены** в MicroPython v1.24.1.

**Существующие макросы:**
- `MP_DEFINE_CONST_FUN_OBJ_0`
- `MP_DEFINE_CONST_FUN_OBJ_1`
- `MP_DEFINE_CONST_FUN_OBJ_2`
- `MP_DEFINE_CONST_FUN_OBJ_3`
- `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN` ← **для 4+ аргументов**

**Решение:**
```c
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(gcm_encrypt_obj, 4, 4, gcm_encrypt);
```

---

## 5. `undefined reference to mbedtls_des3_*`

**Симптом:**
```
undefined reference to `mbedtls_des3_set3key_dec'
undefined reference to `mbedtls_des3_init'
...
```

**Причина:** DES **удалён** из mbedTLS в **ESP-IDF v5.0**. `ucryptography` **использует** 3DES.

**Решение:** создать **заглушки** в `des3_stubs.c`:
```c
#include "mbedtls/des.h"

void mbedtls_des3_init(mbedtls_des3_context *ctx) { (void)ctx; }
void mbedtls_des3_free(mbedtls_des3_context *ctx) { (void)ctx; }
int mbedtls_des3_set3key_enc(mbedtls_des3_context *ctx, const unsigned char key[24]) { return -1; }
...
```

Подключить в `micropython.cmake`:
```cmake
add_library(des3_stubs INTERFACE)
target_sources(des3_stubs INTERFACE ${CMAKE_CURRENT_LIST_DIR}/des3_stubs.c)
target_link_libraries(usermod INTERFACE des3_stubs)
```

---

## 6. `mp_obj_int_to_bytes` не существует

**Симптом:**
```
error: implicit declaration of function 'mp_obj_int_to_bytes'
```

**Причина:** функция **удалена** в MicroPython v1.24.1. Есть только `mp_obj_int_to_bytes_impl`.

**Решение:** обёртка в `modcryptography.c`:
```c
static void mp_obj_int_to_bytes(mp_obj_t obj, size_t len, byte *buf,
                                 bool big_endian, bool signed_flag, bool overflow_check) {
    (void)signed_flag;
    (void)overflow_check;
    mp_obj_int_to_bytes_impl(obj, big_endian, len, buf);
}
```

---

## 7. Ed25519 падает на длинных сообщениях

**Симптом:**
```
InvalidSignature: 0
```
Для сообщений > 96 байт (иногда 100, 110, 120, 128+).

**Причина:** **баг** в `ucryptography` Ed25519 для длинных сообщений.

**Решение:** **перейти на secp256k1** (`usecp256k1` из Bitcoin Core).

---

## 8. Модуль `secp256k1` не найден

**Симптом:**
```
ImportError: no module named 'secp256k1'
```

**Причина:** модуль зарегистрирован как **`usecp256k1`**.

**Решение:**
```python
import usecp256k1  # не secp256k1
```

---

## 9. `keypair_create` возвращает не 2 значения

**Симптом:**
```
ValueError: too many values to unpack (expected 2)
```

**Причина:** функция `keypair_create` **не документирована** и возвращает **больше двух** значений.

**Решение:** **не использовать** `keypair_create`. Использовать:
```python
secret = hashlib.sha256(b"seed").digest()
pubkey_obj = usecp256k1.ec_pubkey_create(secret)
pubkey_bytes = usecp256k1.ec_pubkey_serialize(pubkey_obj, usecp256k1.EC_COMPRESSED)
```

---

## 10. `Wrong boot mode detected`

**Симптом:**
```
ERROR: Failed to connect to ESP32: Wrong boot mode detected (0x13)!
```

**Причина:** ESP32 **не в download mode**.

**Решение:** вручную:
1. Зажать **BOOT**
2. Нажать **EN** (коротко)
3. Отпустить **EN**
4. Отпустить **BOOT**
5. **Сразу** запустить команду

---

## 11. `idf.py: command not found`

**Симптом:**
```
/bin/sh: 1: idf.py: not found
```

**Причина:** ESP-IDF **не активирован** после перезапуска WSL.

**Решение:**
```bash
. ~/esp/esp-idf-v5.2.2/export.sh
```

---

## 12. `Invalid head of packet`

**Симптом:**
```
Invalid head of packet (0xXX)
```

**Причина:** неправильный USB-кабель, плохое питание, ошибки связи.

**Решение:** попробовать другой USB-кабель, другой порт, медленнее baud.

---

## 13. Python-пакеты конфликтуют между ESP-IDF версиями

**Симптом:**
```
The following Python requirements are not satisfied:
Requirement 'esp-idf-kconfig<2.0.0,>=1.4.2' was not met...
```

**Причина:** при переключении между v5.1.2 и v5.2.2 — пакеты конфликтуют.

**Решение:**
```bash
cd ~/esp/esp-idf-v5.2.2
./install.sh esp32
```

---

## 14. Ошибка MicroPico `Exception occurred`

**Симптом:**
```
Error executing commandException occurred
```

**Причина:** MicroPico **завис** или **потерял связь** с ESP32.

**Решение:** 
1. Ctrl+Shift+P → MicroPico: Disconnect
2. Отключить ESP32 от USB
3. Подключить обратно
4. MicroPico: Connect
5. Закрыть/открыть REPL

**Альтернатива:** использовать **miniterm**:
```powershell
py -m serial.tools.miniterm COM3 115200
```

---

## 15. `function doesn't take keyword arguments`

**Симптом:**
```
TypeError: function doesn't take keyword arguments
```

**Причина:** MicroPython **не поддерживает** keyword arguments в некоторых функциях `cryptography`.

**Решение:** использовать **позиционные** аргументы:
```python
mgf = padding.MGF1(hashes.SHA256())
oaep = padding.OAEP(mgf, hashes.SHA256(), None)
```

---

## Сводная таблица

| # | Ошибка | Решение |
|---|---|---|
| 1 | Boot loop | Три файла, три адреса |
| 2 | ESP-IDF несовместим | MicroPython v1.24.1 + IDF v5.2.2 |
| 3 | `STATIC` | Заменить на `static` |
| 4 | `MP_DEFINE_CONST_FUN_OBJ_4` | `MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN` |
| 5 | `mbedtls_des3_*` | Заглушки |
| 6 | `mp_obj_int_to_bytes` | Обёртка |
| 7 | Ed25519 баг | secp256k1 |
| 8 | `secp256k1` не найден | `usecp256k1` |
| 9 | `keypair_create` | Не использовать |
| 10 | Wrong boot mode | Ручной download mode |
| 11 | `idf.py` не найден | Активировать export.sh |
| 12 | Invalid head | Другой кабель |
| 13 | Python-пакеты | install.sh заново |
| 14 | MicroPico завис | miniterm |
| 15 | Keyword args | Позиционные |

