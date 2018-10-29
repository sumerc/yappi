# API reference

**Please note that current version of yappi (v0.82) is not compatible with the older versions.
Lots of existing APIs have been changed.**


### `start(builtins=False, profile_threads=True)`

Starts profiling all threads in the current interpreter instance. 
This function can be called from any thread at any time. 

Resumes profiling if stop() is called previously.

| *Argument*      | *Description*                                                                         |
|-----------------|---------------------------------------------------------------------------------------|
| builtins        | Whether to profile builtin functions, from the Python stdlib.                         |
| profile_threads | Profile all threads if `True`. Otherwise, profile only the calling thread.            |

### `stop()`

Stops the currently running yappi instance. 
Same profiling session might be resumed later by calling `start()`.

### `clear_stats()`

Clears the profiler results. 

All results stay in memory unless application (all threads including the main thread) exits or `clear_stats()` is explicitly called.

### `get_func_stats(filter=None)`

Returns the function stats as a [`YFuncStats`](./YFuncStats.md) object.

<font face='Courier New'> yappi.<b>get\_thread\_stats</b>() </font>

### `get_thread_stats()`

Returns the thread stats as a [`YThreadStats`](./YThreadStats.md) object.

### `is_running()`

Returns a boolean indicating whether profiler is running or not.

### `get_clock_type()`

Returns information about the underlying clock type Yappi should use to measure timing.

### `set_clock_type(type)`

Sets the underlying clock type. `type` must be one of `"wall"` or `"cpu"` .

Read [Clock Types](./clock_types.md) for more.

### `yappi.get_mem_usage()`

Returns the internal memory usage of the profiler itself.

### `convert2pstats(stats)`

Converts the internal stat type of yappi (as returned by `YFuncStats.get()`) to a [`pstats`](https://docs.python.org/3/library/profile.html#module-pstats) object.
