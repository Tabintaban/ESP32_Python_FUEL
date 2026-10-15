"""
time_sync.py — синхронизация времени ESP32 через NTP.

TUR55 раздел 5: проверка `expires` требует точного времени.
NTP даёт текущий Unix timestamp через интернет.

Использование:
    from time_sync import sync_time
    ts = sync_time("ssid", "password")
    if ts:
        loader.set_time(ts)
"""

import network
import time
import ntptime


def _wifi_connect(ssid, password, timeout=15):
    """Подключение к Wi-Fi. Возвращает True/False."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("Wi-Fi already connected:", wlan.ifconfig()[0])
        return True

    print("Connecting to Wi-Fi: %s..." % ssid)
    wlan.connect(ssid, password)

    start = time.time()
    while not wlan.isconnected():
        if time.time() - start > timeout:
            print("Wi-Fi connection failed")
            return False
        time.sleep(1)

    print("Wi-Fi connected:", wlan.ifconfig()[0])
    return True


def sync_time(ssid, password, host="pool.ntp.org", timeout=15,
              retries=3, retry_delay=2):
    """
    Синхронизирует время ESP32 через NTP.

    Args:
        ssid: str — имя Wi-Fi сети
        password: str — пароль
        host: str — NTP-сервер (по умолчанию pool.ntp.org)
        timeout: int — таймаут подключения к Wi-Fi
        retries: int — число попыток NTP
        retry_delay: int — пауза между попытками (сек)

    Returns:
        int — Unix timestamp, или None если ошибка
    """
    # 1. Wi-Fi
    if not _wifi_connect(ssid, password, timeout):
        return None

    # 2. NTP с retry
    ntptime.host = host
    synced = False

    for attempt in range(retries):
        try:
            ntptime.settime()
            synced = True
            break
        except Exception as e:
            print("NTP attempt %d/%d failed: %s" % (attempt + 1, retries, e))
            if attempt < retries - 1:
                time.sleep(retry_delay)

    if not synced:
        print("NTP sync failed after %d attempts" % retries)
        return None

    # 3. Читаем время
    # ntptime.settime() устанавливает RTC в UTC.
    # В MicroPython: time.time() возвращает секунды с 2000-01-01
    # Unix timestamp (с 1970-01-01) = time.time() + 946684800
    EPOCH_OFFSET = 946684800  # 2000-01-01 в Unix
    ts = int(time.time()) + EPOCH_OFFSET

    print("Time synced: %d (Unix)" % ts)
    return ts