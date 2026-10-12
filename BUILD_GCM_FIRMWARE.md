BUILD_GCM_FIRMWARE.md


# Сборка MicroPython с GCM для ESP32-WROOM

**Проверено:** 2026-10-12  
**Результат:** ✅ Работает

## Ключевые версии

| Компонент | Версия | Почему |
|---|---|---|
| MicroPython | **v1.24.1** | Стабильный релиз |
| ESP-IDF | **v5.2.2** | Совместим с v1.24.1 |
| ESP32 | ESP32-D0WDQ6-V3 (WROOM) | Без PSRAM |
| Python (WSL) | 3.10.12 | Требование ESP-IDF |

**Важно:** ESP-IDF **v5.1.2** и **v5.3.2** — **НЕ подходят**. v5.1.2 не в списке поддерживаемых, v5.3.2 требует MicroPython main (v1.30-preview), который не загружается на ESP32-WROOM.

## Что нужно установить

### 1. WSL Ubuntu 22.04

- Python 3.10.12
- git
- cmake, ninja, ccache
- flex, bison, gperf
- libssl-dev, libffi-dev, dfu-util, libusb-1.0-0

### 2. ESP-IDF v5.2.2

```bash
cd ~/esp
git clone -b v5.2.2 --recursive https://github.com/espressif/esp-idf.git esp-idf-v5.2.2
cd esp-idf-v5.2.2
./install.sh esp32
```

### 3. MicroPython v1.24.1

```bash
cd ~
git clone https://github.com/micropython/micropython.git
cd micropython
git checkout v1.24.1
git submodule update --init --recursive
make -C mpy-cross
```

## GCM-модуль

### Структура

```
~/cmodules/
├── micropython.cmake      ← главный
├── des3_stubs.c           ← заглушки 3DES
└── gcm/
    ├── modgcm.c
    └── micropython.cmake
```

### `~/cmodules/gcm/micropython.cmake`

```cmake
add_library(usermod_gcm INTERFACE)

target_sources(usermod_gcm INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/modgcm.c
)

target_include_directories(usermod_gcm INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    /home/tavintavan/esp/esp-idf-v5.2.2/components/mbedtls/mbedtls/include
)

target_link_libraries(usermod INTERFACE usermod_gcm)
```

### `~/cmodules/gcm/modgcm.c`

```c
// modgcm.c — AES-256-GCM для MicroPython ESP32 через mbedTLS
// TUR55 раздел 4.

#include "py/runtime.h"
#include "mbedtls/gcm.h"

// gcm.encrypt(key, iv, pt, aad) -> (ct, tag)
static mp_obj_t gcm_encrypt(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t key, iv, pt, aad;
    mp_get_buffer_raise(args[0], &key, MP_BUFFER_READ);
    mp_get_buffer_raise(args[1], &iv, MP_BUFFER_READ);
    mp_get_buffer_raise(args[2], &pt, MP_BUFFER_READ);
    mp_get_buffer_raise(args[3], &aad, MP_BUFFER_READ);

    if (key.len != 32) {
        mp_raise_ValueError(MP_ERROR_TEXT("key must be 32 bytes"));
    }
    if (iv.len != 12) {
        mp_raise_ValueError(MP_ERROR_TEXT("iv must be 12 bytes"));
    }

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int ret = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key.buf, 256);
    if (ret != 0) {
        mbedtls_gcm_free(&ctx);
        mp_raise_ValueError(MP_ERROR_TEXT("setkey failed"));
    }

    uint8_t *ct = m_new(uint8_t, pt.len ? pt.len : 1);
    uint8_t tag[16];

    ret = mbedtls_gcm_crypt_and_tag(&ctx, MBEDTLS_GCM_ENCRYPT,
        pt.len, iv.buf, iv.len,
        aad.len ? aad.buf : NULL, aad.len,
        pt.buf, ct, 16, tag);
    mbedtls_gcm_free(&ctx);
    if (ret != 0) {
        m_del(uint8_t, ct, pt.len ? pt.len : 1);
        mp_raise_ValueError(MP_ERROR_TEXT("encrypt failed"));
    }

    mp_obj_t tuple[2];
    tuple[0] = mp_obj_new_bytes(ct, pt.len);
    tuple[1] = mp_obj_new_bytes(tag, 16);
    m_del(uint8_t, ct, pt.len ? pt.len : 1);
    return mp_obj_new_tuple(2, tuple);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(gcm_encrypt_obj, 4, 4, gcm_encrypt);

// gcm.decrypt(key, iv, ct, tag, aad) -> pt
static mp_obj_t gcm_decrypt(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t key, iv, ct, tag, aad;
    mp_get_buffer_raise(args[0], &key, MP_BUFFER_READ);
    mp_get_buffer_raise(args[1], &iv, MP_BUFFER_READ);
    mp_get_buffer_raise(args[2], &ct, MP_BUFFER_READ);
    mp_get_buffer_raise(args[3], &tag, MP_BUFFER_READ);
    mp_get_buffer_raise(args[4], &aad, MP_BUFFER_READ);

    if (key.len != 32 || iv.len != 12 || tag.len != 16) {
        mp_raise_ValueError(MP_ERROR_TEXT("bad key/iv/tag length"));
    }

    mbedtls_gcm_context ctx;
    mbedtls_gcm_init(&ctx);
    int ret = mbedtls_gcm_setkey(&ctx, MBEDTLS_CIPHER_ID_AES, key.buf, 256);
    if (ret != 0) {
        mbedtls_gcm_free(&ctx);
        mp_raise_ValueError(MP_ERROR_TEXT("setkey failed"));
    }

    uint8_t *pt = m_new(uint8_t, ct.len ? ct.len : 1);
    ret = mbedtls_gcm_auth_decrypt(&ctx, ct.len,
        iv.buf, iv.len,
        aad.len ? aad.buf : NULL, aad.len,
        tag.buf, 16,
        ct.buf, pt);
    mbedtls_gcm_free(&ctx);
    if (ret != 0) {
        m_del(uint8_t, pt, ct.len ? ct.len : 1);
        mp_raise_ValueError(MP_ERROR_TEXT("authentication failed"));
    }

    mp_obj_t result = mp_obj_new_bytes(pt, ct.len);
    m_del(uint8_t, pt, ct.len ? ct.len : 1);
    return result;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(gcm_decrypt_obj, 5, 5, gcm_decrypt);

static const mp_rom_map_elem_t gcm_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_gcm) },
    { MP_ROM_QSTR(MP_QSTR_encrypt), MP_ROM_PTR(&gcm_encrypt_obj) },
    { MP_ROM_QSTR(MP_QSTR_decrypt), MP_ROM_PTR(&gcm_decrypt_obj) },
};
static MP_DEFINE_CONST_DICT(gcm_module_globals, gcm_module_globals_table);

const mp_obj_module_t gcm_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&gcm_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_gcm, gcm_module);
```

## ucryptography — для RSA-OAEP, BLAKE2s

### Клонировать

```bash
cd ~/esp
git clone https://github.com/dmazzella/ucryptography.git
cd ucryptography
git submodule update --init --depth 1
```

### Патч `mp_obj_int_to_bytes` в `modcryptography.c`

**Найти** `#include "py/objint.h"` и **вставить после**:

```c
// Обёртка для совместимости с MicroPython v1.24.1
static void mp_obj_int_to_bytes(mp_obj_t obj, size_t len, byte *buf,
                                 bool big_endian, bool signed_flag, bool overflow_check) {
    (void)signed_flag;
    (void)overflow_check;
    mp_obj_int_to_bytes_impl(obj, big_endian, len, buf);
}
```

## secp256k1 (Bitcoin Core) — для TUR55

### Клонировать

```bash
cd ~/esp
git clone --recursive https://github.com/MicroPythonOS/secp256k1-embedded-ecdh.git
```

### Проверить флаг

```bash
grep MODULE_SECP256K1 ~/esp/secp256k1-embedded-ecdh/micropython.cmake
```

**Должно быть:** `-DMODULE_SECP256K1_ENABLED=1`.

**Если нет** — добавить:

```bash
sed -i 's/    -DHAVE_CONFIG_H/    -DHAVE_CONFIG_H\n    -DMODULE_SECP256K1_ENABLED=1/' ~/esp/secp256k1-embedded-ecdh/micropython.cmake
```

### Заглушки 3DES

**Файл** `~/cmodules/des3_stubs.c`:

```c
#include "mbedtls/des.h"

void mbedtls_des3_init(mbedtls_des3_context *ctx) { (void)ctx; }
void mbedtls_des3_free(mbedtls_des3_context *ctx) { (void)ctx; }
int mbedtls_des3_set3key_enc(mbedtls_des3_context *ctx, const unsigned char key[24]) { return -1; }
int mbedtls_des3_set3key_dec(mbedtls_des3_context *ctx, const unsigned char key[24]) { return -1; }
int mbedtls_des3_crypt_ecb(mbedtls_des3_context *ctx, const unsigned char input[8], unsigned char output[8]) { return -1; }
int mbedtls_des3_crypt_cbc(mbedtls_des3_context *ctx, int mode, size_t length, unsigned char iv[8], const unsigned char *input, unsigned char *output) { return -1; }
```

### Главный `~/cmodules/micropython.cmake`

```cmake
# Главный micropython.cmake — включает все пользовательские C-модули

# Наш GCM-модуль
include(${CMAKE_CURRENT_LIST_DIR}/gcm/micropython.cmake)

# ucryptography (BLAKE2s, RSA-OAEP, ECDSA)
include(/home/tavintavan/esp/ucryptography/micropython.cmake)

# secp256k1 (Bitcoin Core) — для TUR55
include(/home/tavintavan/esp/secp256k1-embedded-ecdh/micropython.cmake)

# Заглушки для 3DES
add_library(des3_stubs INTERFACE)
target_sources(des3_stubs INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/des3_stubs.c
)
target_link_libraries(usermod INTERFACE des3_stubs)
```

## Сборка прошивки

### 1. Активировать ESP-IDF

```bash
. ~/esp/esp-idf-v5.2.2/export.sh
```

Проверка:

```bash
idf.py --version
```

Должно быть: **ESP-IDF v5.2.2**.

### 2. Собрать MicroPython

```bash
cd ~/micropython/ports/esp32
rm -rf build-ESP32_GENERIC
make BOARD=ESP32_GENERIC USER_C_MODULES=/home/tavintavan/cmodules/micropython.cmake
```

**Время:** 30–60 минут.

### 3. Найти файлы прошивки

```bash
ls -la build-ESP32_GENERIC/bootloader/bootloader.bin
ls -la build-ESP32_GENERIC/partition_table/partition-table.bin
ls -la build-ESP32_GENERIC/micropython.bin
```

## Заливка на ESP32

### ⚠️ ГЛАВНОЕ ПРАВИЛО

**Заливать ТРИ файла по ТРЁМ адресам:**

| Файл | Адрес |
|---|---|
| `bootloader.bin` | `0x1000` |
| `partition-table.bin` | `0x8000` |
| `micropython.bin` | `0x10000` |

**НЕ заливать `micropython.bin` на `0x1000`** — это **причина boot loop**!

### Шаги

#### 1. Скопировать файлы в Windows

```bash
cp ~/micropython/ports/esp32/build-ESP32_GENERIC/bootloader/bootloader.bin /mnt/c/Users/user/Downloads/
cp ~/micropython/ports/esp32/build-ESP32_GENERIC/partition_table/partition-table.bin /mnt/c/Users/user/Downloads/
cp ~/micropython/ports/esp32/build-ESP32_GENERIC/micropython.bin /mnt/c/Users/user/Downloads/
```

#### 2. Стереть flash

**Download mode:** зажать BOOT → нажать EN → отпустить EN → отпустить BOOT.

```powershell
py -m esptool --chip esp32 --port COM3 erase-flash
```

#### 3. Залить три файла

**Снова download mode.**

```powershell
py -m esptool --chip esp32 --port COM3 --baud 460800 write-flash --flash-mode dio --flash-size 4MB --flash-freq 40m -z 0x1000 "C:\Users\user\Downloads\bootloader.bin" 0x8000 "C:\Users\user\Downloads\partition-table.bin" 0x10000 "C:\Users\user\Downloads\micropython.bin"
```

**Ожидаемый вывод:**
```
Writing 'bootloader.bin' at 0x00001000... Hash of data verified.
Writing 'partition-table.bin' at 0x00008000... Hash of data verified.
Writing 'micropython.bin' at 0x00010000... Hash of data verified.
```

## Проверка

```powershell
py -m serial.tools.miniterm COM3 115200
```

**Ожидаемый вывод:**
```
MicroPython v1.24.1 on ...
Type "help()" for more information.
>>> 
```

**Проверить GCM:**
```python
import gcm
key = bytes(32); iv = bytes(12); pt = b'hello'; aad = b''
ct, tag = gcm.encrypt(key, iv, pt, aad)
pt2 = gcm.decrypt(key, iv, ct, tag, aad)
print(pt2)
```

**Ожидаемо:** `b'hello'`

**Проверить secp256k1:**
```python
import usecp256k1
import hashlib
secret = hashlib.sha256(b"test").digest()
pubkey_obj = usecp256k1.ec_pubkey_create(secret)
pubkey = usecp256k1.ec_pubkey_serialize(pubkey_obj, usecp256k1.EC_COMPRESSED)
msg_hash = hashlib.sha256(b"hello").digest()
sig = usecp256k1.ecdsa_sign(msg_hash, secret)
der = usecp256k1.ecdsa_signature_serialize_der(sig)
sig_obj = usecp256k1.ecdsa_signature_parse_der(der)
pubkey_obj2 = usecp256k1.ec_pubkey_parse(pubkey)
ok = usecp256k1.ecdsa_verify(sig_obj, msg_hash, pubkey_obj2)
print('secp256k1 verify:', ok)
```

**Ожидаемо:** `secp256k1 verify: True`

**Проверить RSA-OAEP:**
```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes
sk = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pk = sk.public_key()
mgf = padding.MGF1(hashes.SHA256())
oaep = padding.OAEP(mgf, hashes.SHA256(), None)
ct = pk.encrypt(b'secret', oaep)
pt = sk.decrypt(ct, oaep)
print('RSA-OAEP:', pt)
```

**Ожидаемо:** `RSA-OAEP: b'secret'`

**Выйти:** `Ctrl+]`.

## Частые проблемы

### Boot loop (`RTCWDT_RTC_RESET`)

**Причина:** залили только `micropython.bin` на `0x1000`, без bootloader и partition table.

**Решение:** залить **три файла** по **трём адресам** (см. выше).

### `idf.py: command not found`

**Причина:** ESP-IDF не активирован после перезапуска WSL.

**Решение:**
```bash
. ~/esp/esp-idf-v5.2.2/export.sh
```

### Ошибка версии Python-пакетов

**Причина:** при переключении между версиями ESP-IDF пакеты конфликтуют.

**Решение:** запустить `install.sh` заново:
```bash
cd ~/esp/esp-idf-v5.2.2
./install.sh esp32
```

### `Wrong boot mode detected`

**Причина:** ESP32 не в download mode.

**Решение:** вручную — **зажать BOOT → нажать EN → отпустить EN → отпустить BOOT**.

### `undefined reference to mbedtls_des3_*`

**Причина:** DES удалён в ESP-IDF v5.0.

**Решение:** заглушки `des3_stubs.c` (см. выше).

### `mp_obj_int_to_bytes` не существует

**Причина:** функция удалена в MicroPython v1.24.1.

**Решение:** обёртка в `modcryptography.c` (см. выше).

### Модуль называется `usecp256k1`

**Причина:** `MP_REGISTER_MODULE(MP_QSTR_usecp256k1, ...)`.

**Решение:** `import usecp256k1`, не `secp256k1`.

## Что можно удалить после успеха

Если v5.2.2 работает — **лишние версии ESP-IDF не нужны**:

```bash
rm -rf ~/esp/esp-idf          # v5.1.2
rm -rf ~/esp/esp-idf-v5.3.2   # v5.3.2
```

**Оставить:** только `~/esp/esp-idf-v5.2.2`.

## Ссылки

- MicroPython ESP32 port: https://github.com/micropython/micropython/tree/master/ports/esp32
- ESP-IDF v5.2.2: https://github.com/espressif/esp-idf/tree/v5.2.2
- MicroPython v1.24.1: https://github.com/micropython/micropython/releases/tag/v1.24.1
- mbedTLS GCM API: https://mbed-tls.readthedocs.io/en/latest/kb/how-to/encrypt-with-aes-gcm/
- ucryptography: https://github.com/dmazzella/ucryptography
- secp256k1-embedded-ecdh: https://github.com/MicroPythonOS/secp256k1-embedded-ecdh
```

## Что делать

**1.** Открой `BUILD_GCM_FIRMWARE.md`.
**2.** `Ctrl+A` → `Delete`.
**3.** Вставь **этот полный текст**.
**4.** **Сохрани** (`Ctrl+S`).

**Скажи «готово»** — закоммитим.

**Жду.**