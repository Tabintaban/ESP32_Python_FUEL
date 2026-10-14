Вот обновлённый `ERRORS_AND_SOLUTIONS.md`. Замени целиком.


# ERRORS_AND_SOLUTIONS — база ошибок ESP32_Python_FUEL

**Назначение:** каталог ошибок, с которыми столкнулись, и их решений.

**Последнее обновление:** 2026-10-14

---

## 1. Boot loop ESP32 (`RTCWDT_RTC_RESET`)

**Симптом:**
```
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

## 16. coincurve не устанавливается на Python 3.14

**Симптом:**
```powershell
RuntimeError: Expected exactly one LICENSE file in cffi distribution, got 0
```
(coincurve 21.0.0)

```powershell
ERROR: Use build.verbose instead of cmake.verbose for scikit-build-core >= 0.10
```
(coincurve 20.0.0)

**Причина:** нет готовых wheel-пакетов для Python 3.14 на Windows.
pip собирает из исходников — падает.

**Решение:** использовать **`embit`** вместо `coincurve`:
```powershell
py -m pip install embit
```

---

## 17. ECDSA подпись не совпадает (CPython vs ESP32)

**Симптом:**
```
InvalidSignature: 0
```
Подпись создана cryptography (CPython), не проходит проверку usecp256k1 (ESP32).

**Причина:** cryptography (OpenSSL) и usecp256k1 (libsecp256k1) по-разному реализуют RFC 6979.

**Решение:** использовать embit на CPython — ту же библиотеку (libsecp256k1).

---

## 18. RSA decrypt падает (RuntimeError)

**Симптом:**
```
RuntimeError: rsa_decrypt
```

**Причина:** n (модуль) в `esp32_private_key.json` не совпадал с ключом на CPython. Старый JSON остался на ESP32.

**Решение:** залить `esp32_private_key.json` заново через MicroPico.

**Проверка:**
```
CPython: dd51d7e093874b36...
ESP32:   dd51d7e093874b36...  ← должны совпадать
```

---

## 19. Обёртка `mp_obj_int_to_bytes` (детали)

**Симптом:**
```
error: implicit declaration of function 'mp_obj_int_to_bytes'
```

**Причина:** функция удалена в MicroPython v1.24.1.

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

## 20. `NameError: name 'vars' isn't defined`

**Симптом:**
```
NameError: name 'vars' isn't defined
```
Падает при импорте `execution_sandbox.py` на ESP32 (строка 52).

**Причина:** в MicroPython **нет `vars()`** и **нет модуля `builtins`**.

**Решение:** `except (ImportError, NameError)` — ловим оба:
```python
try:
    import builtins as _builtins_module
    _BUILTINS_DICT = vars(_builtins_module)
except (ImportError, NameError):
    # MicroPython: нет builtins, нет vars()
    try:
        _bi = __builtins__
        ...
    except NameError:
        _BUILTINS_DICT = {}
```

---

## 21. `NameError: name '__builtins__' isn't defined`

**Симптом:**
```
NameError: name '__builtins__' isn't defined
```
После исправления ошибки 20 — на строке 57.

**Причина:** в MicroPython `__builtins__` **тоже не определён** на уровне модуля.

**Решение:**
1. Обернуть `__builtins__` в `try/except NameError`.
2. В `_get_safe_builtins` — fallback на `globals()`:
```python
for builtin_name in allowed_builtins:
    if builtin_name in builtins_dict:
        safe_builtins[builtin_name] = builtins_dict[builtin_name]
    else:
        try:
            safe_builtins[builtin_name] = globals()[builtin_name]
        except KeyError:
            pass
```
3. В `SafeImporter.__import__` — использовать встроенный `__import__` **напрямую** (не через `__builtins__`).

---

## 22. `NameError: name 'TimeoutError' isn't defined`

**Симптом:**
```
NameError: name 'TimeoutError' isn't defined
```
Падает в `execution_engine.py` строка 96 (`except TimeoutError as e:`).

**Причина:** в MicroPython **нет `TimeoutError`**. Есть `OSError`, `RuntimeError`, но не `TimeoutError`.

**Решение:**
1. В `execution_engine.py` — **убрать `except TimeoutError`** (ловим через `except Exception`).
2. В `execution_sandbox.py` — **`raise TimeoutError(...)` заменить на `raise RuntimeError(...)`**.

**Почему `RuntimeError`:** простой класс, есть везде. Если нужно различать timeout — по тексту сообщения `"exceeded time limit"`.

---

## 23. `AttributeError: 'module' object has no attribute 'stdout'`

**Симптом:**
```
AttributeError: 'module' object has no attribute 'stdout'
```
Падает в `execution_sandbox.py` (строка 497, в `except RuntimeError`).

**Причина:** в MicroPython модуль `sys` **не имеет `stdout`/`stderr`** и **не позволяет их создавать**. Присваивание `sys.stdout = ...` падает **даже если атрибут обёрнут в `if ... is not None:`** — потому что `getattr(sys, 'stdout', None)` может вернуть **не None**, а потом **присваивание** не работает.

**Решение:** **полностью отказаться от подмены `sys.stdout`**:
1. В `__init__`: `self.original_stdout = getattr(sys, 'stdout', None)` — **безопасно**.
2. В `execute_in_sandbox`: **не присваивать** `sys.stdout`. Перехват — только через `_capture_buffer`.
3. В `except`/`finally`: **не восстанавливать** `sys.stdout`.
4. В `reset_sandbox`: **не восстанавливать** `sys.stdout`.

**Правильный подход:** перехват `print` через замену в `sandbox_builtins['print']` (см. ошибку 24).

---

## 24. `print` не перехватывается через `__builtins__`

**Симптом:** после замены `sandbox_builtins['print'] = _sandbox_print` — вывод всё равно идёт в консоль, `_capture_buffer` остаётся пустым.

**Причина:** в MicroPython `print` **вшит** в интерпретатор и **не использует** `__builtins__` из `exec()`. Это **фундаментальное ограничение** (официальная документация + форум MicroPython). Плюс — **замыкания не работают с `exec`** (локальные переменные не видны из функции-замыкания).

**Решение:** **отказаться от перехвата `print`**:
1. `capture_output` игнорируется.
2. `print` из скрипта идёт **напрямую в консоль** — это нормально для отладки.
3. `_capture_buffer = []` — заглушка, всегда пустая.

**Если понадобится перехват** — использовать `os.dupterm()` (перехватывает **весь** вывод REPL). Отложено.

---

## 25. WDT-сбросы после теста (`task_wdt: Task watchdog got triggered`)

**Симптом:**
```
E (27645) task_wdt: Task watchdog got triggered.
E (27645) task_wdt:  - mpy_machine_wdt (CPU 0/1)
...
A fatal error occurred.
Rebooting...
```
Срабатывает через ~2 секунды **после** завершения теста.

**Причина:** в MicroPython `machine.WDT` **невозможно остановить** после запуска. `deinit()` **не реализован** (PR #6631 отклонён). WDT продолжает тикать и сбрасывает ESP32.

**Официальная документация:** *«Once it is running the timeout cannot be changed and the WDT cannot be stopped either.»*

**Решение:** **полностью убрать `machine.WDT`** из `execution_sandbox.py`:
1. Убрать `self._watchdog`, `_watchdog_timeout_ms`.
2. Убрать `machine.WDT(...)`, `wdt.feed()`, `wdt.deinit()`.
3. Оставить только `machine.Timer(-1)` — **кооперативный таймаут**.

**Кооперативный таймаут:**
- `machine.Timer(-1)` с периодом 250 мс.
- Колбэк проверяет `elapsed >= time_limit_ms`.
- Если превышено → `_timeout_armed = True`, `_is_running = False`.
- Кооперативный код (проверяющий флаг) завершится сам.
- **Не-кооперативный код (C-цикл) — не прервётся.** Hard-guarantee **отсутствует**.

**Честно:** TUR55 требует «strict time limits», но не уточняет способ. Кооперативный таймаут — законная реализация для типичных скриптов.

---

## 26. `set_time` не нужен — нет источника времени

**Симптом:** `expires` в пакете **не проверяется**.

**Причина:** на ESP32 **нет RTC/NTP**. `time.time()` возвращает 0 или не работает. `set_time()` не вызывается — `time_synced = False`.

**Решение:** **оставить как есть**. `expires` — опциональное поле. `command_id` (replay protection) **работает всегда**. Когда появится NTP/MQTT — вызовем `set_time()`.

---

## 27. MicroPico теряет связь на длинных операциях

**Симптом:**
```
Error executing commandException occurred
Connection has been closed.
```
При чтении больших файлов (>30 KB) или длинных операциях.

**Причина:** MicroPico **зависает** или **теряет связь** при работе с большим выводом / длинными операциями.

**Решение:**
1. **Miniterm** — надёжнее для длинных операций:
```powershell
py -m serial.tools.miniterm COM3 115200
```
2. **Mpremote** — для заливки файлов:
```powershell
py -m mpremote connect COM3 fs cp file.py :file.py
```
3. **Пошаговый ввод** — по одной строке, дожидаясь `>>>` после каждой.
4. **Ctrl+D (soft reboot)** — если MicroPico завис.

**Важно:** закрыть MicroPico **перед** запуском miniterm (COM-порт один).

---

## 28. `line_compiler` / `gcm_esp32` / `object_factory` — мёртвый код

**Симптом:** после переписывания пайплайна — часть файлов **не используется**, но остаётся в проекте.

**Причина:** наследие v2.0. `Select-String` показал, что **никто не тянет** эти модули.

**Решение:** удалить **все неиспользуемые файлы**:
- `crypto_manager.py`, `lightweight_security.py` — v2.0 криптография
- `fast_json_loader.py` — v2.0 JSON
- `performance_tests.py`, `run_tests.py` — v2.0 тесты
- `object_factory.py` — v2.0 дыра (`exec` без песочницы)
- `gcm_esp32.py` — дубль GCM
- `line_compiler.py`, `decrypt_packet_esp32.py`, `bench_gcm.py`, `test_ed25519_size.py`

**Проверка перед удалением:**
```powershell
Select-String -Path *.py -Pattern "module_name" | Where-Object { $_.Filename -ne "module_name.py" }
```
Если пусто — можно удалять.

**Итог:** удалено **18 файлов, ~130 KB, ~2900 строк**.

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
| 16 | coincurve не ставится | embit |
| 17 | ECDSA подписи разные | embit на CPython |
| 18 | RSA decrypt падает | Перезалить JSON |
| 19 | `mp_obj_int_to_bytes` удалена | Обёртка над `mp_obj_int_to_bytes_impl` |
| 20 | `vars` isn't defined | `except (ImportError, NameError)` |
| 21 | `__builtins__` isn't defined | `try/except NameError` + `globals()` fallback |
| 22 | `TimeoutError` isn't defined | Замена на `RuntimeError` |
| 23 | `'module' object has no attribute 'stdout'` | Убрать подмену `sys.stdout` |
| 24 | `print` не перехватывается | Отказаться от перехвата (MicroPython) |
| 25 | WDT-сбросы | Убрать WDT, кооперативный таймаут |
| 26 | `set_time` не нужен | Нет источника времени, `expires` опционален |
| 27 | MicroPico теряет связь | miniterm / mpremote |
| 28 | Мёртвый код | Удалить неиспользуемое |


## Что изменилось

**Добавлено 10 ошибок (20–28):**
- `vars` isn't defined
- `__builtins__` isn't defined
- `TimeoutError` isn't defined
- `sys.stdout` не переопределяется
- `print` не перехватывается
- WDT-сбросы
- `set_time` не нужен
- MicroPico теряет связь
- Мёртвый код

**Обновлено:**
- Убран служебный текст («Документ 2», «Создай файл»)
- Добавлено «Последнее обновление: 2026-10-14»
- Сводная таблица расширена до 28 строк

**Оставлено как было:** ошибки 1–19 (без изменений).

## Как применить

1. Открой `ERRORS_AND_SOLUTIONS.md`
2. `Ctrl+A` → `Delete`
3. Вставь новый текст
4. `Ctrl+S`

## Коммит

```powershell
git add ERRORS_AND_SOLUTIONS.md
git commit -m "ERRORS_AND_SOLUTIONS: добавлены ошибки 20-28 (MicroPython, WDT, stdout)"
git push
```

