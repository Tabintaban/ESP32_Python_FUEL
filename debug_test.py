"""
Debug test for execution_sandbox
"""
from execution_sandbox import ExecutionSandbox

sandbox = ExecutionSandbox(memory_limit_kb=25, time_limit_ms=1000)

test_code = '''
print("Executing in sandbox...")
x = 10
y = 20
result = x + y
print("Result: " + str(result))
'''

result = sandbox.execute_in_sandbox(test_code)
print("Result keys:", result.keys())
print("Success:", result.get('success'))
print("Error:", result.get('error', ''))
print("Output:", result.get('output', ''))