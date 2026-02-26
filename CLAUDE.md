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

## How it works

### Hook mechanism
`yappi.start()` calls `sys.setprofile(_profile_thread_callback)` on the current thread. When a new thread is encountered, yappi transplants its own `c_profilefunc` into the new thread's `PyThreadState` — this is how it profiles all threads without each one needing an explicit `setprofile` call.

Every `call`/`return`/`c_call`/`c_return` event from the interpreter is delivered to `_yappi._profile_event()` (C function).

### Core data structures (C layer)
```
contexts (global htab)
  └── context_id → _ctx
        ├── cs         — call stack (_cstack), tracks the current call chain
        ├── rec_levels — htab tracking recursion depth per function
        ├── t0         — profiling start tick
        ├── sched_cnt  — how many times this thread was scheduled
        └── tags (htab)
              └── tag_id → pits (htab)
                    └── code_obj / m_ml → _pit (profile item)
                          ├── callcount, nonrecursive_callcount
                          ├── ttotal   — total time including children
                          ├── tsubtotal — self time (excluding children)
                          ├── children — linked list of _pit_children_info (callee timing per caller-callee pair)
                          └── coroutines — linked list of _coro (active coroutine frames + start tick)
```

### Contexts
A *context* maps to a thread by default. Context identity is stored as `_yappi_tid` in `ThreadState.dict` — a monotonic counter rather than the OS tid (which can be recycled). This design allows alternative context backends: for **greenlets**, a `context_id_callback` returns a per-greenlet ID so multiple greenlets sharing one OS thread appear as separate contexts.

### Tags
An optional `tag_callback` returns an integer per call event. Stats are bucketed per `(context, tag)`, allowing you to segregate profiling data (e.g. by request, task type, etc.) without separate profiling sessions.

### Coroutines
Each `_pit` (function) holds a linked list of `_coro` entries — one per concurrently suspended coroutine frame. When a coroutine is suspended (`FRAME_SUSPENDED`), its elapsed time is accumulated into the `_coro` entry without closing the `_pit`. On resumption, timing continues from where it left off. This correctly handles multiple concurrent coroutines calling the same function.

### Stat collection (Python layer)
`get_func_stats()` / `get_thread_stats()` enumerate the C-side hash tables and materialize them as Python objects:

| C struct | Python wrapper | Collection |
|----------|---------------|------------|
| `_pit`   | `YFuncStat`   | `YFuncStats` |
| `_ctx`   | `YThreadStat` | `YThreadStats` |

`YFuncStat.children` is a `YChildFuncStats` collection (from `_pit_children_info`) representing direct callees with per-pair timing. Export formats (callgrind, pstat) are produced by converting these collections in Python.

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
