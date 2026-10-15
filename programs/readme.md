# programs/

Папка для пакетов TUR55 (офлайн-доставка).

## Назначение

Если у ESP32 **нет сети** (MQTT/Wi-Fi), пакет можно доставить **физически**:
через USB-флешку или прямо через кабель (MicroPico, mpremote).

Это соответствует **TUR55 тезис 8** (Transport Freedom) —
пакет может прийти **любым транспортом**.

## Имя файла

`program.enc` — фиксированное имя, которое ищет `main.py`.

## Как положить

**Через mpremote:**

```powershell
py -m mpremote connect COM3 fs cp program.enc :programs/program.enc