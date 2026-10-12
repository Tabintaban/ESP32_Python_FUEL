from program_loader import ProgramLoader

loader = ProgramLoader()

with open('test_packet.bin', 'rb') as f:
    packet = f.read()

print('Packet size:', len(packet), 'bytes')

data = loader.load_program(packet)
print('command_id:', data['command_id'])
print('device_id: ', data['device_id'])
print('permissions:', data['execution']['permissions'])
print('OK')