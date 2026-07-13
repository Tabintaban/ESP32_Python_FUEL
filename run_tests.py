"""
Run all tests and write results to file
"""
import sys
import io

# Redirect stdout to capture all output
output = io.StringIO()
sys.stdout = output

print("=" * 60)
print("TEST 1: memory_optimizer")
print("=" * 60)
from memory_optimizer import test_memory_optimizer
test_memory_optimizer()

print("=" * 60)
print("TEST 2: execution_sandbox")
print("=" * 60)
from execution_sandbox import test_execution_sandbox
test_execution_sandbox()

print("=" * 60)
print("TEST 3: execution_engine")
print("=" * 60)
from execution_engine import test_execution_engine
test_execution_engine()

print("=" * 60)
print("TEST 4: crypto_manager")
print("=" * 60)
from crypto_manager import test_crypto_manager
test_crypto_manager()

print("=" * 60)
print("TEST 5: crypto_manager HMAC fallback")
print("=" * 60)
from crypto_manager import test_hmac_fallback_security
test_hmac_fallback_security()

print("=" * 60)
print("TEST 6: lightweight_security")
print("=" * 60)
from lightweight_security import test_lightweight_security
test_lightweight_security()

print("=" * 60)
print("TEST 7: lightweight_security HMAC fallback")
print("=" * 60)
from lightweight_security import test_hmac_fallback_security
test_hmac_fallback_security()

print("=" * 60)
print("ALL TESTS COMPLETED")
print("=" * 60)

# Restore stdout and write to file
sys.stdout = sys.__stdout__
with open('test_results.txt', 'w', encoding='utf-8') as f:
    f.write(output.getvalue())

print("Tests completed. Results written to test_results.txt")