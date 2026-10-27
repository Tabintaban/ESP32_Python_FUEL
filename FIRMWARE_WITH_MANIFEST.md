# Прошивка с manifest.py (freeze + gc.threshold)

**Дата:** 2026-10-21
**Статус:** ✅ Приёмка пройдена (MVP end-to-end с TUR55_Executor)
**Цель:** MicroPython-прошивка с замороженными Python-модулями (freeze) и `gc.threshold`.

**Связанный документ:** [BUILD_GCM_FIRMWARE.md](BUILD_GCM_FIRMWARE.md) — базовая сборка (C-модули: GCM, ucryptography, secp256k1).

---

## Что добавлено к базовой сборке

| Что | Зачем | Где |
|---|---|---|
| **`manifest.py`** | Заморозка Python-модулей в прошивку | Корень проекта ESP32_Python_FUEL |
| **`FROZEN_MANIFEST`** | Флаг `make` для сборки с манифестом | Команда `make` |
| **`mqtt_client.py`** | MQTT-приём на ESP32 (транспорт Delivery) | `manifest.py` (freeze) |
| **`gc.threshold(1024)`** | Обход нехватки RAM при инициализации RSA-ключа | `main.py`, строка 22 |

**Без `manifest.py` и `gc.threshold`** — ошибка `RuntimeError: rsa_private_numbers` (нехватка RAM).

---

## `manifest.py`

```python
# manifest.py — заморозка Python-модулей в прошивку
include("$(PORT_DIR)/boards/manifest.py")

freeze(".", (
    "main.py",
    "program_loader.py",
    "execution_engine.py",
    "execution_sandbox.py",
    "tur55_packet.py",
    "gcm_adapter.py",
    "time_sync.py",
    "mqtt_client.py",
))
```

**Где лежит:** `C:\Users\user\Documents\Projects\ESP32_Python_FUEL\manifest.py`

**Что делает:** при сборке MicroPython «вшивает» эти `.py` файлы в прошивку (`.mpy` внутри `micropython.bin`). Код исполняется из Flash, а не из RAM.

---

## `gc.threshold(1024)` в `main.py`

**Файл:** `main.py`, строка 22 (после `import gc`).

```python
import gc
gc.threshold(1024)   # ← добавлено
```

**Что делает:** GC срабатывает каждые 1024 байта выделенной памяти → меньше фрагментации → хватает RAM для `ProgramLoader` (RSA-ключ).

---

## Сборка прошивки

### 1. Активировать ESP-IDF (WSL)

```bash
. ~/esp/esp-idf-v5.2.2/export.sh
```

### 2. Перейти в порт ESP32

```bash
cd ~/micropython/ports/esp32
```

### 3. Очистить старую сборку

```bash
rm -rf build-ESP32_GENERIC
```

### 4. Собрать с `FROZEN_MANIFEST`

```bash
make BOARD=ESP32_GENERIC \
  USER_C_MODULES=/home/tavintavan/cmodules/micropython.cmake \
  FROZEN_MANIFEST=/mnt/c/Users/user/Documents/Projects/ESP32_Python_FUEL/manifest.py \
  -j8
```

**Ожидаем:**
```
Project build complete.
...
application @0x010000  1882880  (  148736 remaining)
```

**Размер:** ~1.88 МБ (влезает в factory 1.9 МБ).

### 5. Скопировать файлы в Windows

```bash
cp ~/micropython/ports/esp32/build-ESP32_GENERIC/bootloader/bootloader.bin /mnt/c/Users/user/Downloads/
cp ~/micropython/ports/esp32/build-ESP32_GENERIC/partition_table/partition-table.bin /mnt/c/Users/user/Downloads/
cp ~/micropython/ports/esp32/build-ESP32_GENERIC/micropython.bin /mnt/c/Users/user/Downloads/
```

---

## Заливка прошивки

### 1. Стереть flash (PowerShell)

ESP32 в download mode: **зажать BOOT → нажать EN → отпустить EN → отпустить BOOT**.

```powershell
py -m esptool --chip esp32 --port COM3 erase-flash
```

### 2. Залить три файла

Снова download mode.

```powershell
py -m esptool --chip esp32 --port COM3 --baud 460800 write-flash --flash-mode dio --flash-size 4MB --flash-freq 40m -z `
  0x1000 "C:\Users\user\Downloads\bootloader.bin" `
  0x8000 "C:\Users\user\Downloads\partition-table.bin" `
  0x10000 "C:\Users\user\Downloads\micropython.bin"
```

**Ожидаем:** `Hash of data verified` × 3.

---

## Заливка файлов данных (mpremote)

После прошивки — залить ключи и пакет:

```powershell
py -m mpremote connect COM3 mkdir :programs
py -m mpremote connect COM3 cp "C:\Users\user\Documents\Projects\ESP32_Python_FUEL\esp32_private_key.json" :esp32_private_key.json
py -m mpremote connect COM3 cp "C:\Users\user\Documents\Projects\TUR55_Executor\keys\executor_pubkey.bin" :executor_pubkey.bin
py -m mpremote connect COM3 cp "C:\Users\user\Documents\Projects\TUR55_Executor\outputfiles\program.enc" :programs/program.enc
```

**Проверка:**
```powershell
py -m mpremote connect COM3 exec "import os; print(os.listdir('programs'))"
```

**Ожидаем:** `['program.enc']`.

---

## Проверка

**В REPL ESP32 (miniterm):**

```python
import main
main.main()
```

**Ожидаем:**
```
[INFO] === TUR55 Pipeline ===
[INFO] Auto-found packet: programs/program.enc
[INFO] Init ProgramLoader...
[INFO] Init ExecutionEngine...
[INFO] Executing program (max_iterations=240)...
[INFO] setup success:    True
[INFO] loop iterations:  240
[INFO] loop time_ms:     243505
[INFO] === Done ===
```

**Лампочка мигала и выключилась.**

---

## Что было до (без manifest.py)

| Проблема | Причина | Решение |
|---|---|---|
| `RuntimeError: rsa_private_numbers` | Нехватка RAM (RSA-2048 + `ucryptography`) | `gc.threshold(1024)` + `freeze` |
| `max_iterations=5` жёстко | `main.py` | Чтение из пакета (`execution.max_iterations`) |

**Ошибка исчезла** после добавления `freeze` + `gc.threshold`.

---

## Приёмка (21.10.2026)

| Что | Результат |
|---|---|
| Пакет (`program.enc`) | 988 байт (с `max_iterations: 240`) |
| `parse_packet` | ✅ |
| Подпись (ECDSA secp256k1) | ✅ |
| `setup success` | ✅ `True` |
| `loop iterations` | ✅ `240` |
| Время мигания | ✅ ~4 минуты (MicroPython `sleep` чуть больше 0.5) |
| Результат | ✅ **MVP end-to-end работает** |

---

## Что важно помнить

- **`manifest.py`** — **не секрет**, можно коммитить (в git).
- **`keys/`, `outputfiles/program.enc`, `logs/`** — **секрет/временное** (в `.gitignore`).
- **Изменение `main.py` (например, `max_iterations` логика)** — **требует пересборки** (`.mpy` заморожен).
- **Изменение `program.enc`** — **не требует пересборки** (заливается через `mpremote`).

---

## Важно: `boot.py` и `umqtt.robust`

С версии **v3.5.0** (26.10.2026) в проекте появились два изменения, которые важно учитывать при сборке и заливке:

### 1. `boot.py` не замораживается

- **`boot.py` не включён** в `manifest.py`.
- Он выполняется при каждом включении ESP32 (до `main.py`).
- Его можно менять на диске без пересборки прошивки (залить через `mpremote fs cp`).
- В нём реализована автоматическая NTP-синхронизация (см. `CHANGELOG.md` v3.5.0, `DECISIONS_LOG.md` решение №34).

### 2. `mqtt_client.py` требует `umqtt.robust`

- С версии **v3.5.0** `mqtt_client.py` использует **`umqtt.robust`** вместо `umqtt.simple`.
- В стандартной прошивке MicroPython `umqtt.robust` **уже включён**.
- Если вы собираете кастомную прошивку — проверьте наличие `lib/umqtt/robust.py`.
- Если `umqtt.robust` отсутствует, `mqtt_client.py` выдаст `ImportError: umqtt.robust not installed`.

---

## Ссылки

- **BUILD_GCM_FIRMWARE.md** — базовая сборка (C-модули).
- **DECISIONS_LOG.md** — решения 27 (`max_iterations`), 28 (`manifest.py`), 29 (`gc.threshold`).
- **CHANGELOG.md** — v3.4.0 (приёмка MVP).
- **TUR55_Executor/HANDOFF.md** — сторона Executor.
```
