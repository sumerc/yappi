# yappi — Developer Guide

## Overview
yappi is a C-extension Python profiler (`yappi/_yappi.c` + `yappi/yappi.py`). The C layer handles all profiling hooks via `sys.setprofile`; the Python layer provides the public API and stat containers.

## Python version policy
**Single codebase, no version branches. We adopt new Python versions as soon as possible and drop EOL versions promptly — supporting all non-EOL versions at any given time.**

All Python code must run unmodified across the entire supported range. Before using any language feature or stdlib addition, verify it is available in the oldest currently supported non-EOL version. In `_yappi.c`, use `PY_VERSION_HEX` guards for version-specific C-API usage (see existing `>= 0x030B0000` guards).

## Running tests
```bash
# Install with test deps (once)
pip install -e ".[test]"

# Run all tests
python run_tests.py

# Run a specific module
python run_tests.py test_functionality

# Run a specific test
python -m pytest tests/test_functionality.py::ClassName::test_name -v
```
Test infrastructure: `unittest` via `run_tests.py`. Base class in `tests/utils.py` (`YappiUnitTestCase`) resets all yappi state in `setUp`.

## Architecture
```
yappi/_yappi.c       — C extension: profiling hooks, stat storage, GIL management
yappi/yappi.py       — Public API: start/stop/clear_stats, stat wrappers, export (callgrind, pstat)
tests/               — All tests (unittest)
  test_functionality.py  — Core feature tests
  test_hooks.py          — Callback/hook tests
  test_tags.py           — Tag-based profiling
  test_asyncio*.py       — Async/coroutine profiling
  utils.py               — Shared helpers and base test class
```

## Key constraints
- **Don't assume GIL protection in callbacks**: profiler callbacks can fire on any thread; C code must be thread-safe
- **clear_stats() sequence**: pause → wait for in-flight callbacks → clear. Never free memory while callbacks may still be running
- **`_callback_depth`**: volatile counter in C tracking in-flight callbacks. `_wait_for_callbacks()` spins until 0, releasing GIL during wait
- The C extension uses custom memory allocators (`mem.h`) and a hash table (`hashtab.h`) — avoid `malloc`/`free` directly

## Build
```bash
pip install -e ".[test]"              # editable install with test deps
python setup.py build_ext --inplace   # rebuild C extension only (faster iteration on C code)
```
`pip install -e .` calls `build_ext` internally; use `--inplace` directly only when iterating on C code without reinstalling.
