Понял. Создаю **полную инструкцию** по сборке прошивки с GCM — со всеми версиями, командами и **решением проблемы заливки**.

## Создай файл `BUILD_GCM_FIRMWARE.md`

В папке проекта: `C:\Users\user\documents\projects\esp32_python_fuel\BUILD_GCM_FIRMWARE.md`

**Содержимое:**

```markdown
# Сборка MicroPython с GCM для ESP32-WROOM

**Проверено:** 2026-10-10  
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
~/cmodules/gcm/
├── modgcm.c
└── micropython.cmake
```

### `micropython.cmake`

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

**Важно:** путь к mbedTLS **абсолютный** и **указывает на v5.2.2**.

### `modgcm.c` — минимальный (для проверки)

```c
#include "py/runtime.h"

static mp_obj_t gcm_test(void) {
    return mp_obj_new_str("ok", 2);
}
static MP_DEFINE_CONST_FUN_OBJ_0(gcm_test_obj, gcm_test);

static const mp_rom_map_elem_t gcm_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_gcm) },
    { MP_ROM_QSTR(MP_QSTR_test), MP_ROM_PTR(&gcm_test_obj) },
};
static MP_DEFINE_CONST_DICT(gcm_module_globals, gcm_module_globals_table);

const mp_obj_module_t gcm_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&gcm_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_gcm, gcm_module);
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
make BOARD=ESP32_GENERIC USER_C_MODULES=/home/tavintavan/cmodules/gcm/micropython.cmake
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
gcm.test()
```

**Ожидаемо:** `'ok'`

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
```

## Дальше

1. **Создай файл** `BUILD_GCM_FIRMWARE.md`.
2. **Вставь** содержимое.
3. **Сохрани**.

**Скажи, когда готово** — закоммитим и запушим.

**Жду.**