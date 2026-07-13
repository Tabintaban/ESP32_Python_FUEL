"""
Run all tests with clear output
"""
import sys
import io

# Redirect stdout to capture all output
output = io.StringIO()
sys.stdout = output

print("=" * 70)
print("ESP32 PYTHON FUEL - TEST SUITE")
print("=" * 70)
print()

print("=" * 70)
print("TEST 1: memory_optimizer")
print("=" * 70)
from tests.test_memory_optimizer import test_memory_optimizer
test_memory_optimizer()

print("=" * 70)
print("TEST 2: execution_sandbox")
print("=" * 70)
from tests.test_execution_sandbox import test_execution_sandbox, test_sandbox_timeout, test_memory_monitoring
test_execution_sandbox()
test_sandbox_timeout()
test_memory_monitoring()

print("=" * 70)
print("TEST 3: execution_engine")
print("=" * 70)
from tests.test_execution_engine import test_execution_engine
test_execution_engine()

print("=" * 70)
print("TEST 4: crypto_manager")
print("=" * 70)
from tests.test_crypto_manager import test_crypto_manager, test_hmac_fallback_security
test_crypto_manager()
test_hmac_fallback_security()

print("=" * 70)
print("TEST 5: lightweight_security")
print("=" * 70)
from tests.test_lightweight_security import test_lightweight_security, test_hmac_fallback_security as test_hmac_fallback_security_lw
test_lightweight_security()
test_hmac_fallback_security_lw()

print("=" * 70)
print("ALL TESTS COMPLETED SUCCESSFULLY")
print("=" * 70)
print()

# Restore stdout and write to file
sys.stdout = sys.__stdout__
with open('test_results.txt', 'w', encoding='utf-8') as f:
    f.write(output.getvalue())

print("Tests completed. Results written to test_results.txt")
print()
print("Summary:")
print("-" * 70)
print("✓ memory_optimizer tests passed")
print("✓ execution_sandbox tests passed (including timeout and memory monitoring)")
print("✓ execution_engine tests passed")
print("✓ crypto_manager tests passed (including HMAC fallback security)")
print("✓ lightweight_security tests passed (including HMAC fallback security)")
print("-" * 70)