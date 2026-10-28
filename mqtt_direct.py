"""
mqtt_direct.py — MQTT-клиент на чистом сокете (обход getaddrinfo).

Подключается к локальному брокеру (192.168.0.100) по IP, без DNS.
Отправляет CONNECT, SUBSCRIBE, слушает PUBLISH.
При получении пакета сохраняет его в programs/program.enc.
"""

import socket
import network
import time
import os
import secrets

BROKER_IP = "192.168.0.103"
BROKER_PORT = 1883
TOPIC = "tur55/device/esp32_001"
CLIENT_ID = "esp32_direct"
OUTPUT_FILE = "programs/program.enc"

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        for _ in range(20):
            if wlan.isconnected():
                break
            time.sleep(1)
    if not wlan.isconnected():
        raise RuntimeError("Wi-Fi failed")
    print("Wi-Fi OK:", wlan.ifconfig()[0])

def encode_remaining_length(length):
    """Кодирует оставшуюся длину MQTT-пакета (variable-length)."""
    out = bytearray()
    while True:
        byte = length % 128
        length //= 128
        if length > 0:
            byte |= 0x80
        out.append(byte)
        if length == 0:
            break
    return bytes(out)

def build_connect_packet(client_id):
    """Собирает MQTT CONNECT-пакет."""
    var_header = b'\x00\x04MQTT\x04\x02\x00\x3c'
    payload = len(client_id).to_bytes(2, 'big') + client_id.encode()
    remaining = var_header + payload
    return b'\x10' + encode_remaining_length(len(remaining)) + remaining

def build_subscribe_packet(topic, packet_id=1):
    """Собирает MQTT SUBSCRIBE-пакет."""
    var_header = packet_id.to_bytes(2, 'big')
    payload = len(topic).to_bytes(2, 'big') + topic.encode() + b'\x00'  # QoS 0
    remaining = var_header + payload
    return b'\x82' + encode_remaining_length(len(remaining)) + remaining

def read_remaining_length(sock):
    """Читает variable-length из сокета."""
    multiplier = 1
    value = 0
    while True:
        byte = sock.recv(1)
        if not byte:
            return None
        b = byte[0]
        value += (b & 0x7f) * multiplier
        if (b & 0x80) == 0:
            break
        multiplier *= 128
    return value

def main():
    connect_wifi()

    print("Connecting to broker %s:%d..." % (BROKER_IP, BROKER_PORT))
    sock = socket.socket()
    sock.settimeout(10)  # Таймаут 10 секунд, чтобы не висеть вечно на recv
    sock.connect((BROKER_IP, BROKER_PORT))

    # CONNECT
    sock.send(build_connect_packet(CLIENT_ID))
    connack = sock.recv(4)
    if len(connack) < 4 or connack[0] != 0x20:
        raise RuntimeError("CONNECT failed: %r" % connack)
    print("CONNECT OK")

    # SUBSCRIBE
    sock.send(build_subscribe_packet(TOPIC))
    suback = sock.recv(5)
    if len(suback) < 5 or suback[0] != 0x90:
        raise RuntimeError("SUBSCRIBE failed: %r" % suback)
    print("SUBSCRIBED to", TOPIC)

    print("Waiting for PUBLISH...")
    last_ping = time.time()
    
    while True:
        try:
            # Отправляем PINGREQ каждые 20 секунд
            if time.time() - last_ping > 20:
                sock.send(b'\xc0\x00')  # PINGREQ
                last_ping = time.time()
            
            header = sock.recv(1)
            if not header:
                print("Socket closed by broker. Reconnecting...")
                break
            
            ptype = header[0] >> 4
            if ptype == 3:  # PUBLISH
                qos = (header[0] >> 1) & 0x03
                remaining = read_remaining_length(sock)
                if remaining is None:
                    break
                topic_len = int.from_bytes(sock.recv(2), 'big')
                topic = sock.recv(topic_len).decode()
                if qos > 0:
                    sock.recv(2)
                payload = sock.recv(remaining - 2 - topic_len - (2 if qos > 0 else 0))
                print("!!! GOT PACKET !!!", len(payload), "bytes on", topic)
                try:
                    os.mkdir("programs")
                except OSError:
                    pass  # уже существует
                with open(OUTPUT_FILE, "wb") as f:
                    f.write(payload)
                print("Saved to", OUTPUT_FILE)
                break
            elif ptype == 6:  # PUBREL
                continue
            elif ptype == 13:  # PINGRESP
                continue
            else:
                remaining = read_remaining_length(sock)
                if remaining:
                    sock.recv(remaining)
        except OSError as e:
            if e.args[0] == 116:  # ETIMEDOUT — просто ждём дальше
                continue
            else:
                print("Socket error:", e)
                break

    sock.close()

if __name__ == "__main__":
    main()