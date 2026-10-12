"""
ProgramLoader — загрузка и валидация программ TUR55.

Схема (TUR55 Layer 4):
  пакет TUR55 (bytes) -> parse_packet() -> JSON -> валидация конверта 3.2

Загрузчик НЕ знает, откуда пришёл пакет:
  - из сети (MQTT/HTTP/BLE)
  - из файла (programs/program.enc)
Это соответствует TUR55 тезис 8 (Transport Freedom).

Ключи загружаются один раз в __init__():
  - esp32_private_key  <- esp32_private_key.json (RSA-OAEP)
  - executor_pubkey    <- executor_pubkey.bin (secp256k1, 33 байта)

Пока не eFuse — это отдельный этап.
"""

import json
import gc

import tur55_packet


# Обязательные поля конверта TUR55 (раздел 3.2)
CONVERT_FIELDS = (
    'tur55_version',
    'command_id',
    'device_id',
    'source',
    'execution',
    'custom_data',
)

# Обязательные поля внутри execution
EXECUTION_FIELDS = (
    'runtime_limit_ms',
    'memory_limit_kb',
    'permissions',
)

SAFE_PERMISSIONS = ('gpio', 'time', 'math', 'struct', 'json')


class ProgramLoader:
    """
    Загрузчик и валидатор программ TUR55.

    Отвечает за:
      - чтение пакета TUR55 (байты)
      - дешифрование и проверку подписи (через tur55_packet.parse_packet)
      - валидацию конверта 3.2
      - проверку разрешений и лимитов
      - кэширование загруженных программ

    НЕ отвечает за:
      - раскладку execution на setup/loop_logic (это execution_engine)
      - проверку expires/command_id (это Заход 2)
    """

    KEY_PATH = 'esp32_private_key.json'
    PUBKEY_PATH = 'executor_pubkey.bin'
    CACHE_LIMIT = 10

    def __init__(self):
        self.esp32_private_key = self._load_private_key()
        self.executor_pubkey = self._load_executor_pubkey()

        self.loaded_programs = {}
        self.validation_cache = {}

        # Заход 2: replay protection (в RAM, позже — NVS)
        self.used_command_ids = set()

    # ------------------------------------------------------------------
    # Загрузка ключей
    # ------------------------------------------------------------------

    def _load_private_key(self):
        """Загружает RSA-приватный ключ ESP32 из JSON."""
        try:
            with open(self.KEY_PATH, 'r') as f:
                key_data = json.load(f)
        except OSError as e:
            raise OSError("Cannot read %s: %s" % (self.KEY_PATH, e))

        try:
            from cryptography.hazmat.primitives.asymmetric import rsa

            def _hex_or_int(v):
                return int(v, 16) if isinstance(v, str) else int(v)

            n = _hex_or_int(key_data['n'])
            e = _hex_or_int(key_data['e'])
            d = _hex_or_int(key_data['d'])
            p = _hex_or_int(key_data['p'])
            q = _hex_or_int(key_data['q'])
            dmp1 = _hex_or_int(key_data['dmp1'])
            dmq1 = _hex_or_int(key_data['dmq1'])
            iqmp = _hex_or_int(key_data['iqmp'])

            pub_numbers = rsa.RSAPublicNumbers(e, n)
            priv_numbers = rsa.RSAPrivateNumbers(
                p, q, d, dmp1, dmq1, iqmp, pub_numbers
            )
            return priv_numbers.private_key()

        except (KeyError, ValueError) as e:
            raise ValueError("Invalid private key format: %s" % e)

    def _load_executor_pubkey(self):
        """Загружает публичный ключ экзекутора (33 байта compressed)."""
        try:
            with open(self.PUBKEY_PATH, 'rb') as f:
                pubkey = f.read()
        except OSError as e:
            raise OSError("Cannot read %s: %s" % (self.PUBKEY_PATH, e))

        if len(pubkey) != 33:
            raise ValueError(
                "Executor pubkey must be 33 bytes, got %d" % len(pubkey)
            )
        return pubkey

    # ------------------------------------------------------------------
    # Основной вход
    # ------------------------------------------------------------------

    def load_program(self, packet_bytes):
        """
        Загружает программу из пакета TUR55 (байты).

        Args:
            packet_bytes: bytes — пакет TUR55

        Returns:
            dict — расшифрованный и провалидированный JSON (конверт 3.2)
        """
        if not isinstance(packet_bytes, (bytes, bytearray)):
            raise TypeError("packet_bytes must be bytes or bytearray")

        # 1. Разбор, дешифрование, проверка подписи
        try:
            program_data = tur55_packet.parse_packet(
                bytes(packet_bytes),
                self.esp32_private_key,
                self.executor_pubkey,
            )
        except ValueError as e:
            raise ValueError("Packet parse failed: %s" % e)

        # 2. Валидация конверта 3.2
        if not self.validate_program_structure(program_data):
            raise ValueError("Invalid TUR55 envelope (section 3.2)")

        # 3. Разрешения
        if not self.validate_permissions(program_data):
            raise ValueError("Permission denied")

        # 4. Лимиты времени/памяти
        if not self.validate_runtime_constraints(program_data):
            raise ValueError("Runtime constraints invalid")

        # 5. Кэш по command_id
        program_id = program_data.get('command_id')
        self.cache_program(program_id, program_data)

        return program_data

    def load_program_from_file(self, filepath):
        """
        Обёртка: читает файл и передаёт байты в load_program().

        Args:
            filepath: str — путь к файлу пакета

        Returns:
            dict — расшифрованный JSON
        """
        try:
            with open(filepath, 'rb') as f:
                packet_bytes = f.read()
        except OSError as e:
            raise OSError("Cannot read program file %s: %s" % (filepath, e))

        return self.load_program(packet_bytes)

    # ------------------------------------------------------------------
    # Валидация конверта 3.2
    # ------------------------------------------------------------------

    def validate_program_structure(self, program_data):
        """
        Проверяет конверт TUR55 раздел 3.2.

        Обязательные поля верхнего уровня:
          tur55_version, command_id, device_id, source, execution, custom_data

        Обязательные поля внутри execution:
          runtime_limit_ms, memory_limit_kb, permissions
        """
        if not isinstance(program_data, dict):
            return False

        # Верхний уровень
        for field in CONVERT_FIELDS:
            if field not in program_data:
                return False

        if not isinstance(program_data['tur55_version'], str):
            return False

        if (not isinstance(program_data['command_id'], str)
                or not program_data['command_id']):
            return False

        if not isinstance(program_data['device_id'], str):
            return False

        if not isinstance(program_data['source'], dict):
            return False

        if not isinstance(program_data['custom_data'], dict):
            return False

        # execution
        execution = program_data['execution']
        if not isinstance(execution, dict):
            return False

        for field in EXECUTION_FIELDS:
            if field not in execution:
                return False

        if 'setup' in execution and not isinstance(execution['setup'], list):
            return False
        if 'loop_logic' in execution and not isinstance(execution['loop_logic'], list):
            return False
        if 'functions' in execution and not isinstance(execution['functions'], list):
            return False

        # Хотя бы что-то должно быть исполняемым
        if 'setup' not in execution and 'loop_logic' not in execution:
            return False

        return True

    # ------------------------------------------------------------------
    # Разрешения
    # ------------------------------------------------------------------

    def validate_permissions(self, program_data):
        """
        Проверяет разрешения программы (TUR55 раздел 6).
        Разрешения лежат в execution.permissions.
        """
        execution = program_data.get('execution', {})
        permissions = execution.get('permissions', [])

        if not isinstance(permissions, list):
            return False

        for perm in permissions:
            if perm not in SAFE_PERMISSIONS:
                return False

        return True

    # ------------------------------------------------------------------
    # Лимиты
    # ------------------------------------------------------------------

    def validate_runtime_constraints(self, program_data):
        """
        Проверяет лимиты времени и памяти.
        Лимиты лежат в execution.
        """
        execution = program_data.get('execution', {})

        runtime_limit = execution.get('runtime_limit_ms', 5000)
        memory_limit = execution.get('memory_limit_kb', 50)

        if not isinstance(runtime_limit, int):
            return False
        if not isinstance(memory_limit, int):
            return False

        if runtime_limit <= 0 or runtime_limit > 30000:
            return False
        if memory_limit <= 0 or memory_limit > 100:
            return False

        return True

    # ------------------------------------------------------------------
    # Кэш
    # ------------------------------------------------------------------

    def cache_program(self, program_id, program_data):
        """Кэширует программу. Лимит — CACHE_LIMIT (FIFO)."""
        if program_id is None:
            return
        self.loaded_programs[program_id] = program_data
        if len(self.loaded_programs) > self.CACHE_LIMIT:
            oldest_key = next(iter(self.loaded_programs))
            del self.loaded_programs[oldest_key]

    def get_cached_program(self, program_id):
        """Возвращает программу из кэша или None."""
        return self.loaded_programs.get(program_id)

    def clear_cache(self):
        """Очищает кэш и вызывает gc."""
        self.loaded_programs.clear()
        self.validation_cache.clear()
        gc.collect()

    # ------------------------------------------------------------------
    # Хелперы
    # ------------------------------------------------------------------

    def get_program_metadata(self, program_data):
        """Метаданные программы (source + custom_data)."""
        return {
            'source': program_data.get('source', {}),
            'custom_data': program_data.get('custom_data', {}),
        }

    def get_program_config(self, program_data):
        """Конфигурация выполнения (execution)."""
        return program_data.get('execution', {})


# ----------------------------------------------------------------------
# Пример использования
# ----------------------------------------------------------------------
if __name__ == '__main__':
    loader = ProgramLoader()

    # Из файла
    # data = loader.load_program_from_file('programs/program.enc')
    # print('command_id:', data['command_id'])

    # Из сети (байты)
    # packet = mqtt_client.receive()
    # data = loader.load_program(packet)
    # print('command_id:', data['command_id'])

    print("ProgramLoader ready.")