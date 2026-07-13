"""
Run all tests and write results to file
"""
import sys
import io

# Redirect stdout
old_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
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
    print("ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 60)

except Exception as e:
    print(f"\nFATAL ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

finally:
    # Save output
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    with open('test_results.txt', 'w', encoding='utf-8') as f:
        f.write(output)
    print("Results written to test_results.txt")
    print(output[-500:] if len(output) > 500 else output)