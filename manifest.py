# manifest.py
# Включаем стандартный манифест порта ESP32, чтобы не потерять его модули.
include("$(PORT_DIR)/boards/manifest.py")

# Замораживаем наши Python-модули.
# Путь "." означает, что файлы берутся из директории, где запускается сборка.
freeze(".", (
    "main.py",
    "program_loader.py",
    "execution_engine.py",
    "execution_sandbox.py",
    "tur55_packet.py",
    "gcm_adapter.py",
    "time_sync.py",
    # Добавьте сюда другие .py файлы, которые используются в проекте
))
