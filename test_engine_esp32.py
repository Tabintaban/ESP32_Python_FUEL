"""
Тест execution_engine на ESP32.

Загружает test_packet_engine.bin, прогоняет через:
  ProgramLoader -> ExecutionEngine
"""

from program_loader import ProgramLoader
from execution_engine import ExecutionEngine

print("=" * 40)
print("engine test (ESP32)")
print("=" * 40)

# 1. ProgramLoader
print("1. ProgramLoader...")
loader = ProgramLoader()
print("   OK")

# 2. Загрузка пакета
print("2. Loading test_packet_engine.bin...")
with open("test_packet_engine.bin", "rb") as f:
    packet = f.read()
print("   Packet size:", len(packet))

# 3. load_program
print("3. load_program...")
data = loader.load_program(packet)
print("   command_id:", data['command_id'])
print("   device_id: ", data['device_id'])

# 4. ExecutionEngine
print("4. ExecutionEngine...")
engine = ExecutionEngine(memory_limit_kb=50, time_limit_ms=9000)
print("   OK")

# 5. execute_program
print("5. execute_program...")
result = engine.execute_program(data, max_iterations=5)
print("   success:", result.get('success'))

# 6. Проверки
print("6. Results:")
setup_result = result.get('setup_result', {})
loop_result = result.get('loop_result', {})
print("   setup success:", setup_result.get('success'))
print("   setup error:  ", setup_result.get('error'))
print("   setup output: ", setup_result.get('output'))
print("   result error: ", result.get('error'))
print("   loop iterations:", loop_result.get('iterations_completed'))

print("=" * 40)
print("DONE")
print("=" * 40)