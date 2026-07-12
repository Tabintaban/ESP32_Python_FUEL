# ESP32 Secure Program Execution System

## Overview

This project implements a secure system for ESP32 using MicroPython that allows dynamic loading, decrypting, and executing programs from encrypted JSON files. The system provides high performance, security, and isolated code execution.

## Architecture

The system consists of the following components:

1. **CryptoManager** - Handles encryption/decryption using AES-CTR + HMAC-SHA256 (Encrypt-then-MAC)
2. **ObjectFactory** - Creates dynamic objects with method injection from JSON
3. **ExecutionSandbox** - Executes code in a secure, limited environment with SafeImporter
4. **ProgramLoader** - Loads and validates programs from encrypted JSON files
5. **FastJSONLoader** - Optimized JSON parser with newline preservation and syntax validation
6. **LineBasedCompiler** - Efficiently compiles line-based code with safe indent normalization
7. **ExecutionEngine** - Executes programs with caching, hot-swapping, and thread-based timeout
8. **LightweightSecurity** - HMAC-SHA256 signature verification with replay protection
9. **MemoryOptimizer** - Manages memory with pre-execution checking and runtime monitoring

## Features

### Security
- AES-CTR + HMAC-SHA256 encryption (Encrypt-then-MAC scheme)
- HMAC-SHA256 signature verification with replay protection (nonce/timestamp)
- Isolated execution in sandbox with SafeImporter (module whitelist)
- Blocked dangerous builtins: __import__, eval, exec, compile, getattr, setattr, delattr
- Constant-time comparison for tag verification (prevents timing attacks)
- Thread-based timeout mechanism for interrupting hung code
- Pre-execution memory checking and runtime monitoring
- Safe indent normalization (prevents tabs/spaces mixing)
- Structured logging with levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Performance
- Load to execution time < 500ms
- RAM consumption < 50KB per program
- Hot-reload support without restart
- Compiled code caching

### ESP32 Optimizations
- Uses bytearray instead of str where possible
- Pre-allocated buffers
- Memory monitoring and cleanup
- Batch data processing

## Requirements

- ESP32 microcontroller
- MicroPython firmware with:
  - File system (LittleFS/SPIFFS)
  - Cryptographic operations (AES/ChaCha20)
  - JSON parsing

## Installation

 1. Flash your ESP32 with MicroPython
 2. Copy all `.py` files to the ESP32 file system
 3. Create a `programs/` directory for encrypted program files
 4. Create a `data/` directory for decrypted HTML, CSS, and JS files

## Usage

The system now works with two types of folders:
- `programs/` - for encrypted program files
- `data/` - for decrypted HTML, CSS, and JS files

### Basic Usage
```python
from fast_json_loader import FastJSONLoader
from line_compiler import LineBasedCompiler
from execution_engine import ExecutionEngine

# Initialize components
loader = FastJSONLoader()
compiler = LineBasedCompiler()
engine = ExecutionEngine()

# Load and execute program
json_data = loader.load_encrypted("programs/program.enc.json", device_key)
code_blocks = loader.extract_code_lines(json_data)
executable = compiler.build_executable(code_blocks)

# Execute setup and loop
engine.execute_setup(executable['setup'])
engine.execute_loop(executable['loop_logic'], max_iterations=1000)
```

### Complete System
Run the main system with:
```python
import main
main.main()
```

### Performance Testing
Run performance benchmarks with:
```python
import performance_tests
performance_tests.run_performance_tests()
```

## JSON Program Format

```json
{
  "metadata": {
    "version": "1.0",
    "signature": "ed25519_signature_here",
    "timestamp": "2023-12-01T10:00:00Z",
    "checksum": "sha256_checksum",
    "author": "Author Name",
    "description": "Program description"
  },
  "config": {
    "runtime_limit_ms": 5000,
    "memory_limit_kb": 25,
    "permissions": ["gpio", "time"],
    "hot_reload_enabled": true
  },
  "imports": [
    "import machine",
    "import time"
  ],
  "functions": [
    "def blink_led(pin, duration):",
    "    pin.value(1)",
    "    time.sleep(duration)",
    "    pin.value(0)",
    "    time.sleep(duration)"
  ],
  "setup": [
    "led_pin = machine.Pin(2, machine.Pin.OUT)"
  ],
  "loop_logic": [
    "blink_led(led_pin, 0.5)",
    "time.sleep(1)"
  ]
}
```

## Security Measures

1. **Encryption**: All program files are AES-CTR + HMAC-SHA256 encrypted (Encrypt-then-MAC)
2. **Signature Verification**: HMAC-SHA256 signatures with replay protection (nonce/timestamp)
3. **Sandbox Execution**: Code runs in limited environment with SafeImporter (module whitelist)
4. **Permission Control**: Restricted access to dangerous functions (blocked: __import__, eval, exec, compile, getattr, setattr, delattr)
5. **Resource Limits**: Time and memory constraints enforced with thread-based timeout
6. **Input Sanitization**: All inputs are validated and cleaned
7. **Timing Attack Protection**: Constant-time comparison for tag verification
8. **Memory Safety**: Pre-execution memory checking and runtime monitoring

## Performance Benchmarks

The system meets these performance targets:
- File load time: < 100ms
- Decryption time: < 150ms
- Compilation time: < 100ms
- Execution startup: < 150ms
- Total time: < 500ms
- Memory usage: < 50KB per program

## Example: LED Control Program

The repository includes an example LED control program (`led_control_program.json`) that demonstrates:
- GPIO control
- Timing functions
- Loop execution
- State management

## Memory Management

The system includes a MemoryOptimizer that:
- Pre-allocates buffers to reduce fragmentation
- Monitors memory usage
- Performs garbage collection when needed
- Optimizes bytearray usage

## Testing

The system includes comprehensive testing modules:
- `performance_tests.py`: Measures system performance
- Built-in validation in each component
- Security checks throughout the pipeline

## Limitations

- MicroPython's limited standard library affects some cryptographic operations
- Memory constraints on ESP32 limit program complexity
- No real-time OS features for hard timing guarantees

## Recent Security Fixes (v2.0)

This version includes critical security fixes:

- **crypto_manager.py**: Replaced fake AES-GCM with proper AES-CTR + HMAC-SHA256 (Encrypt-then-MAC), added constant-time comparison
- **lightweight_security.py**: Replaced broken Ed25519 with HMAC-SHA256 signature, removed insecure `_derive_private_from_public()`, added replay protection
- **execution_sandbox.py**: Removed `__import__` from allowed builtins, implemented SafeImporter with module whitelist, blocked getattr/setattr/delattr
- **execution_engine.py**: Added thread-based timeout mechanism for interrupting hung code
- **memory_optimizer.py**: Added pre-execution memory checking and runtime monitoring with RealTimeMemoryMonitor
- **fast_json_loader.py**: Fixed newline preservation in combine_code_sections, added syntax validation
- **line_compiler.py**: Implemented safe indent normalization with GCD-based detection, prevents tabs/spaces mixing
- **main.py**: Replaced broad exception handling with specific exceptions, implemented Logger class with levels

## Future Improvements

- Enhanced memory management algorithms
- More sophisticated permission systems
- Additional encryption algorithms support

## License

This project is released under the MIT License.