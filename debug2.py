"""
Debug 2: check what's in safe_builtins
"""
from execution_sandbox import ExecutionSandbox

s = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=1000)
print("safe_builtins keys:", sorted(s.safe_builtins.keys()))
print("has print:", 'print' in s.safe_builtins)
print("print type:", type(s.safe_builtins.get('print')))

# Try a minimal code
try:
    result = s.execute_in_sandbox("x=1", capture_output=False)
    print("result:", result)
except Exception as e:
    print("Exception:", type(e).__name__, ":", e)