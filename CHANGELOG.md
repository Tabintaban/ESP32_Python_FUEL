# Changelog

All notable changes to the ESP32 Secure Program Execution System will be documented in this file.

## [2.0.0] - 2024-01-XX

### Security Fixes (Critical)

#### crypto_manager.py
- **Replaced fake AES-GCM with proper AES-CTR + HMAC-SHA256 (Encrypt-then-MAC)**
  - Uses separate encryption_key and hmac_key (both 32 bytes)
  - Implements constant-time comparison for tag verification (prevents timing attacks)
  - Unique IV generation for each encryption
  - Added unit tests for encryption/decryption correctness, tampering detection, IV uniqueness, and timing attack resistance

#### lightweight_security.py
- **Replaced broken Ed25519 with HMAC-SHA256 symmetric signature**
  - Removed insecure `_derive_private_from_public()` method (critical security flaw)
  - Signature now requires secret key knowledge
  - Added nonce/timestamp for replay attack protection
  - Implemented constant-time comparison for signature verification
  - Moved getattr, setattr, delattr from safe to unsafe functions
  - Added unit tests for signature verification, forgery prevention, and replay protection

#### execution_sandbox.py
- **Removed `__import__` from allowed_builtins (critical security flaw)**
  - Implemented SafeImporter class with module whitelist
  - Blocked relative imports above level 0
  - Added RESTRICTED_GLOBALS dict to block dangerous builtins
  - Blocked getattr, setattr, delattr (can be used for sandbox bypass)
  - Added unit tests for import blocking, eval blocking, and allowed module import

#### execution_engine.py
- **Added thread-based timeout mechanism for interrupting hung code**
  - Implemented TimeoutExecutionEngine class with _thread support
  - Configurable timeout for execution limits
  - Proper resource cleanup after timeout
  - Fallback to non-threaded execution when _thread unavailable
  - Added unit tests for timeout on slow code and resource cleanup

#### memory_optimizer.py
- **Added pre-execution memory checking and runtime monitoring**
  - Implemented RealTimeMemoryMonitor class
  - check_before_execution() validates memory before code execution
  - check_during_execution() monitors memory during execution
  - Auto-trigger gc.collect() near memory limits
  - Added detailed memory statistics (free, allocated, total)
  - Added unit tests for memory checking and stats

#### fast_json_loader.py
- **Fixed newline preservation in combine_code_sections**
  - Proper handling of trailing whitespace between sections
  - Added syntax validation before returning combined code
  - Preserves code structure while cleaning up
  - Added unit tests for newline preservation, syntax validation, and trailing whitespace handling

#### line_compiler.py
- **Implemented safe indent normalization**
  - GCD-based indent size detection (supports 2 and 4 spaces)
  - Prevents mixing tabs and spaces (raises IndentationError)
  - Converts tabs to spaces for consistency
  - Preserves code semantics during normalization
  - Added unit tests for indent detection, normalization, and tab/space mixing detection

#### main.py
- **Replaced broad exception handling with specific exceptions**
  - Implemented Logger class with levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Specific handling for FileNotFoundError, MemoryError, ValueError, OSError
  - Only use broad Exception for unexpected errors with re-raise
  - Structured logging throughout the application

### Testing
- Added unit tests to all fixed modules (crypto_manager.py, lightweight_security.py, execution_sandbox.py, execution_engine.py, memory_optimizer.py, fast_json_loader.py, line_compiler.py)
- All tests are compatible with MicroPython

### Documentation
- Updated README.md with security fix details
- Created CHANGELOG.md to document changes

## [1.0.0] - Initial Release

### Features
- AES-GCM encryption for JSON files
- Ed25519-like signature verification
- Isolated execution in sandbox
- Fast JSON loading and compilation
- Memory optimization for ESP32
- Hot-reload support
- Performance benchmarks (< 500ms load to execution)
