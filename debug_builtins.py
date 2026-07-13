import sys
sys.path.insert(0, '.')

# Проверяем глобальный _BUILTINS_DICT
from execution_sandbox import _BUILTINS_DICT
print("Type:", type(_BUILTINS_DICT))
if isinstance(_BUILTINS_DICT, dict):
    print("Len:", len(_BUILTINS_DICT))
    print("Has print:", 'print' in _BUILTINS_DICT)
    print("First 10 keys:", list(_BUILTINS_DICT.keys())[:10])

# Проверяем safe_builtins
from execution_sandbox import ExecutionSandbox
s = ExecutionSandbox(25, 1000)
print("\nsafe_builtins type:", type(s.safe_builtins))
print("safe_builtins len:", len(s.safe_builtins))
print("safe_builtins has print:", 'print' in s.safe_builtins)
print("safe_builtins keys:", sorted(s.safe_builtins.keys()))