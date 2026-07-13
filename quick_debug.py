"""Direct debug test"""
from execution_sandbox import ExecutionSandbox

s = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=1000)
print("Builtins have print:", 'print' in s.safe_builtins)
r = s.execute_in_sandbox("print(123)")
print("Result:", r)
print("Success:", r.get('success'))
print("Error:", r.get('error',''))
print("Output:", repr(r.get('output','')))