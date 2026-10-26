"""
mqtt_client.py — приём пакетов TUR55 по MQTT на ESP32.

TUR55 Delivery Layer: пакет приходит по MQTT вместо файла.
Загрузчик (program_loader) не знает, откуда пришёл пакет.

Использование:
    from mqtt_client import MQTTReceiver
    receiver = MQTTReceiver("ssid", "password", "44.232.241.40")
    receiver.connect()
    packet = receiver.wait_for_packet("tur55/device/esp32_001", timeout=30)
    receiver.disconnect()
    # packet -> program_loader.load_program(packet)
"""

import network
import time
import gc

try:
    from umqtt.robust import MQTTClient
except ImportError:
    MQTTClient = None


class MQTTReceiver:
    """Приёмник пакетов TUR55 по MQTT."""

    def __init__(self, ssid, password, broker, port=1883, client_id=None):
        self.ssid = ssid
        self.password = password
        self.broker = broker
        self.port = port
        self.client_id = client_id or "esp32_tur55"
        self.client = None
        self._received_packet = None

    def _wifi_connect(self, timeout=15):
        """Подключение к Wi-Fi."""
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        if wlan.isconnected():
            print("Wi-Fi already connected:", wlan.ifconfig()[0])
            return True

        print("Connecting to Wi-Fi: %s..." % self.ssid)
        wlan.connect(self.ssid, self.password)

        start = time.time()
        while not wlan.isconnected():
            if time.time() - start > timeout:
                print("Wi-Fi connection failed")
                return False
            time.sleep(1)

        print("Wi-Fi connected:", wlan.ifconfig()[0])
        return True

    def _on_message(self, topic, msg):
        """Callback при получении MQTT-сообщения."""
        print("MQTT message on %s: %d bytes" % (topic, len(msg)))
        self._received_packet = msg

    def connect(self):
        """Подключение к Wi-Fi + MQTT брокеру."""
        if MQTTClient is None:
            raise ImportError("umqtt.robust not installed")

        if not self._wifi_connect():
            return False

        print("Connecting to MQTT broker: %s:%d..." % (self.broker, self.port))
        self.client = MQTTClient(self.client_id, self.broker, port=self.port)
        self.client.set_callback(self._on_message)
        self.client.connect()
        print("MQTT connected")
        return True

    def subscribe(self, topic):
        """Подписка на топик."""
        if self.client is None:
            raise RuntimeError("Not connected")
        self.client.subscribe(topic)
        print("Subscribed to: %s" % topic)

    def wait_for_packet(self, topic, timeout=30):
        """
        Ждёт пакет TUR55 на топике.

        Args:
            topic: str — MQTT-топик
            timeout: int — таймаут в секундах

        Returns:
            bytes — пакет, или None если таймаут
        """
        if self.client is None:
            raise RuntimeError("Not connected")

        self.subscribe(topic)
        self._received_packet = None

        start = time.time()
        while time.time() - start < timeout:
            self.client.check_msg()
            if self._received_packet is not None:
                packet = self._received_packet
                self._received_packet = None
                return packet
            time.sleep(0.1)

        print("Timeout waiting for packet")
        return None

    def disconnect(self):
        """Отключение от MQTT."""
        if self.client is not None:
            try:
                self.client.disconnect()
            except Exception:
                pass
            self.client = None
        gc.collect()