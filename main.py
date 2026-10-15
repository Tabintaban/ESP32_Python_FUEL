"""
main.py — главная точка входа ESP32_Python_FUEL.

Пайплайн TUR55 (Layer 4):
    пакет -> parse_packet -> validate конверта 3.2 -> execute_program

Что делает:
    1. ProgramLoader — загрузка ключей, parse пакета, validate
    2. ExecutionEngine — setup + loop в песочнице
    3. Логирование результата

Расширенная версия (когда появится потребность):
    - set_time(current_time)  — синхронизация времени для проверки expires
    - run_from_bytes(packet)  — приём пакета из сети (MQTT/HTTP/BLE)
    - run_batch(paths)        — выполнение нескольких пакетов подряд
    - hot_swap(path)          — замена программы без перезагрузки
    - eFuse                   — хранение ключей в аппаратном модуле
    - NVS                     — хранение used_command_ids между перезагрузками
"""

import gc

from program_loader import ProgramLoader
from execution_engine import ExecutionEngine


class Logger:
    """
    Класс для логирования с уровнями (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """

    def __init__(self, level="INFO"):
        self.levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4,
        }
        self.current_level = self.levels.get(level, 1)

    def log(self, level, message):
        if self.levels.get(level, 0) >= self.current_level:
            print("[%s] %s" % (level, message))

    def debug(self, message):
        self.log('DEBUG', message)

    def info(self, message):
        self.log('INFO', message)

    def warning(self, message):
        self.log('WARNING', message)

    def error(self, message):
        self.log('ERROR', message)

    def critical(self, message):
        self.log('CRITICAL', message)

def _find_packet():
    """
    Ищет пакет TUR55.

    Порядок (TUR55 тезис 8, Transport Freedom):
      1. programs/program.enc   — офлайн-доставка (флешка, USB)
      2. test_packet_engine.bin — для тестов

    Returns:
        str — путь к пакету, или None если не найдено
    """
    candidates = [
        "programs/program.enc",
        "test_packet_engine.bin",
    ]
    for path in candidates:
        try:
            with open(path, 'rb') as f:
                f.read(1)
            return path
        except OSError:
            continue
    return None



def run_program(packet_path=None, max_iterations=5, log_level="INFO",
                wifi_ssid=None, wifi_password=None):
    """
    Основной пайплайн TUR55: загрузка пакета -> валидация -> выполнение.

    Args:
        packet_path: str | None — путь к файлу пакета TUR55
            (если None — ищет programs/program.enc, потом test_packet_engine.bin)
        max_iterations: int — лимит итераций loop
        log_level: str — уровень логирования
        wifi_ssid: str | None — SSID Wi-Fi (для NTP-синхронизации времени)
        wifi_password: str | None — пароль Wi-Fi

    Returns:
        dict — {'success': ..., 'setup_result': ..., 'loop_result': ...}
    """
    logger = Logger(level=log_level)
    logger.info("=== TUR55 Pipeline ===")

    # 0. Поиск пакета, если путь не задан
    if packet_path is None:
        packet_path = _find_packet()
        if packet_path is None:
            logger.error("No packet found (programs/program.enc, test_packet_engine.bin)")
            return {'success': False, 'error': 'No packet found'}
        logger.info("Auto-found packet: %s" % packet_path)

       # 1. ProgramLoader — ключи + parse + validate
    logger.info("Init ProgramLoader...")
    loader = ProgramLoader()

    # 1.5. NTP-синхронизация времени (опционально)
    # NTP доступен только на ESP32 (нужны network + ntptime)
    try:
        import network  # noqa: F401
        has_network = True
    except ImportError:
        has_network = False

    if wifi_ssid and wifi_password and has_network:
        logger.info("Syncing time via NTP...")
        try:
            from time_sync import sync_time
            ts = sync_time(wifi_ssid, wifi_password)
            if ts:
                loader.set_time(ts)
                logger.info("Time synced: %d" % ts)
            else:
                logger.warning("NTP sync failed — expires not checked")
        except Exception as e:
            logger.warning("NTP sync error: %s" % e)
    elif not has_network:
        logger.info("NTP skipped (no network module — CPython)")
    else:
        logger.info("NTP skipped (no Wi-Fi credentials)")

    # 2. ExecutionEngine — sandbox + setup/loop
    logger.info("Init ExecutionEngine...")
    engine = ExecutionEngine() 

    # 3. Загрузка и валидация пакета
    logger.info("Loading packet: %s" % packet_path)
    data = loader.load_program_from_file(packet_path)

    logger.info("command_id: %s" % data.get('command_id'))
    logger.info("device_id:  %s" % data.get('device_id'))

    execution = data.get('execution', {})
    logger.info("permissions: %s" % execution.get('permissions'))
    logger.info("runtime_limit_ms: %s" % execution.get('runtime_limit_ms'))
    logger.info("memory_limit_kb:  %s" % execution.get('memory_limit_kb'))

    # 4. Выполнение
    logger.info("Executing program (max_iterations=%d)..." % max_iterations)
    result = engine.execute_program(data, max_iterations=max_iterations)

    if not result.get('success'):
        logger.error("Execution failed: %s" % result.get('error'))
        return result

    setup_result = result.get('setup_result', {})
    loop_result = result.get('loop_result', {})

    logger.info("setup success:    %s" % setup_result.get('success'))
    logger.info("loop iterations:  %s" % loop_result.get('iterations_completed'))
    logger.info("loop time_ms:     %s" % loop_result.get('execution_time_ms'))

    # 5. Статистика sandbox
    stats = engine.get_execution_stats()
    logger.info("contexts:  %d" % stats.get('contexts_count', 0))
    logger.info("cached:    %d" % stats.get('cached_programs_count', 0))

    logger.info("=== Done ===")
    return result


def main():
    """
    Стандартный вход: выполнить test_packet_engine.bin.

    Если есть secrets.py — использует Wi-Fi для NTP-синхронизации.
    """
    # Опционально: Wi-Fi из secrets.py
    wifi_ssid = None
    wifi_password = None
    try:
        from secrets import WIFI_SSID, WIFI_PASSWORD
        wifi_ssid = WIFI_SSID
        wifi_password = WIFI_PASSWORD
    except ImportError:
        pass  # secrets.py нет — работаем без NTP

    try:
        run_program(max_iterations=5,
                    wifi_ssid=wifi_ssid, wifi_password=wifi_password)

    except MemoryError as e:
        print("[CRITICAL] Out of memory: %s" % e)

    except ValueError as e:
        print("[ERROR] Validation failed: %s" % e)

    except OSError as e:
        print("[ERROR] File system error: %s" % e)

    except Exception as e:
        print("[CRITICAL] Unexpected error: %s: %s" % (type(e).__name__, e))
        raise

    finally:
        gc.collect()


if __name__ == "__main__":
    main()