"""
mqtt_publisher.py — отправка пакетов TUR55 на ESP32 через MQTT.

Использование (Windows PowerShell):
    py mqtt_publisher.py

Отправляет test_packet_engine.bin на брокер broker.hivemq.com
в топик tur55/device/esp32_001.
"""

import time
import sys

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("ERROR: paho-mqtt not installed")
    print("Install: py -m pip install paho-mqtt")
    sys.exit(1)


# --- Настройки ---
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC = "tur55/device/esp32_001"
PACKET_FILE = "test_packet_engine.bin"


def main():
    print("=" * 50)
    print("TUR55 MQTT Publisher")
    print("=" * 50)

    # 1. Читаем пакет
    print("\n1. Reading packet: %s" % PACKET_FILE)
    try:
        with open(PACKET_FILE, "rb") as f:
            packet = f.read()
    except OSError as e:
        print("ERROR: %s" % e)
        return 1

    print("   Packet size: %d bytes" % len(packet))

    # 2. Подключаемся к брокеру
    print("\n2. Connecting to broker: %s:%d" % (BROKER, PORT))

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("   Connected")
        else:
            print("   Connection failed: rc=%s" % rc)

    def on_publish(client, userdata, mid, reason_code=None, properties=None):
        print("   Published (mid=%s)" % mid)

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        client.connect(BROKER, PORT, 60)
    except Exception as e:
        print("ERROR: %s" % e)
        return 1

    client.loop_start()
    time.sleep(1)

    # 3. Публикуем пакет
    print("\n3. Publishing to: %s" % TOPIC)
    client.publish(TOPIC, packet, qos=1)
    time.sleep(2)

    # 4. Отключаемся
    print("\n4. Disconnecting...")
    client.loop_stop()
    client.disconnect()

    print("\n" + "=" * 50)
    print("Done")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())