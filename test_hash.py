import struct
import hashlib

packet = open('test_packet.bin', 'rb').read()
header = packet[:8]
pubkey_part = packet[8:42]
sk_len = packet[42] * 256 + packet[43]
session_key_part = packet[42:44+sk_len]
offset = 44 + sk_len
offset += 12
ct_len = struct.unpack('>I', packet[offset:offset+4])[0]
offset += 4 + ct_len + 16
script_part = packet[44+sk_len:offset]
data_to_verify = header + pubkey_part + session_key_part + script_part
msg_hash = hashlib.sha256(data_to_verify).digest()
print('CPython hash:', msg_hash.hex())
print('ESP32 hash:  8aa74cc7d94f50808429e51c2be4bc43f4638384c557a9be7cab19d202e2f484')
print('Match:', msg_hash.hex() == '8aa74cc7d94f50808429e51c2be4bc43f4638384c557a9be7cab19d202e2f484')