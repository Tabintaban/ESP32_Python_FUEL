import network
import time
import ntptime
import secrets
from machine import reset

# ==========================================
# НАСТРОЙКИ NTP (по IP, чтобы обойти DNS и блокировки)
# ==========================================
NTP_SERVERS = [
    "216.239.35.8",    # time.google.com (проверен с вашего ПК)
    "162.159.200.1",   # time.cloudflare.com
    "129.6.15.28",     # time.nist.gov
]

def sync_time_with_retry():
    """Пытается синхронизировать время по списку NTP-серверов."""
    for server_ip in NTP_SERVERS:
        print(f"[NTP] Trying {server_ip}...")
        for attempt in range(1, 4):  # 3 попытки на каждый сервер
            try:
                ntptime.host = server_ip
                ntptime.settime()
                print(f"[NTP] SUCCESS! Time synced: {time.time()}")
                return True
            except OSError as e:
                print(f"[NTP] Attempt {attempt}/3 failed: {e}")
                time.sleep(2)
    print("[NTP] ALL SERVERS FAILED.")
    return False

def main_boot():
    print("[BOOT] Starting...")
    
    # 1. Подключение к Wi-Fi
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("[BOOT] Connecting to Wi-Fi...")
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        # Ждем до 20 секунд
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    
    if not wlan.isconnected():
        print("[BOOT] Wi-Fi FAILED. Rebooting in 10s...")
        time.sleep(10)
        reset()
    
    print(f"[BOOT] Wi-Fi OK: {wlan.ifconfig()[0]}")
    
    # 2. Синхронизация времени
    if not sync_time_with_retry():
        print("[BOOT] Time sync failed. Rebooting in 10s...")
        time.sleep(10)
        reset()
    
    print("[BOOT] Boot sequence complete. Starting main.py...")

# Запускаем только при старте (не при soft reboot из REPL)
if __name__ == "__main__":
    main_boot()