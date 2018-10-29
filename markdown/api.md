# API reference

**Please note that current version of yappi (v0.82) is not compatible with the older versions.
Lots of existing APIs have been changed.**

## Functions

#### `start(builtins=False, profile_threads=True)`

Starts profiling all threads in the current interpreter instance. 
This function can be called from any thread at any time. 

Resumes profiling if stop() is called previously.

| *Argument*      | *Description*                                                                         |
|-----------------|---------------------------------------------------------------------------------------|
| `builtins`        | Whether to profile builtin functions, from the Python stdlib.                         |
| `profile_threads` | Profile all threads if `True`. Otherwise, profile only the calling thread.            |

#### `stop()`

Stops the currently running yappi instance. 
Same profiling session might be resumed later by calling `start()`.

#### `clear_stats()`

Clears the profiler results. 

All results stay in memory unless application (all threads including the main thread) exits or `clear_stats()` is explicitly called.

#### `get_func_stats(filter=None)`

Returns the function stats as a [`YFuncStats`](./YFuncStats.md) object.

<font face='Courier New'> yappi.<b>get\_thread\_stats</b>() </font>

#### `get_thread_stats()`

Returns the thread stats as a [`YThreadStats`](./YThreadStats.md) object.

#### `is_running()`

Returns a boolean indicating whether profiler is running or not.

#### `get_clock_type()`

Returns information about the underlying clock type Yappi should use to measure timing.

#### `set_clock_type(type)`

Sets the underlying clock type. `type` must be one of `"wall"` or `"cpu"` .

Read [Clock Types](./clock_types.md) for more.

#### `yappi.get_mem_usage()`

Returns the internal memory usage of the profiler itself.

#### `convert2pstats(stats)`

Converts the internal stat type of yappi (as returned by `YFuncStats.get()`) to a [`pstats`](https://docs.python.org/3/library/profile.html#module-pstats) object.

# Classes

## `YFuncStats` (*new in v0.82*)


| *Attribute*  | *Description*                                                                   |
|-------------|---------------------------------------------------------------------------------|
| `name`        | Name of the executed function                                                   |
| `module`      | Module name of the executed function                                            |
| `lineno`      | Line number of the executed function                                            |
| `ncall`       | number of times the executed function is called.                                |
| `nactualcall` | number of times the executed function is called, excluding the recursive calls. |
| `builtin`     | bool, indicating whether the executed function is a builtin                   |
| `ttot`        | total time spent in the executed function                                       |
| `tsub`        | total time spent in theexecuted function, excluding subcalls                    |
| `index`       | A unique number for the stat                                                    |
| `children`    | list of functionscalled from the executed function                              |
| `ctx_id`      |                                                                                 |
| `tavg`        | per-call average total time spent in the executed function.                     |
| `full_name`   | unique full name of the executed function                                       |



#### `get()`

This method retrieves the current profiling stats.      

`yappi.get_func_stats()` is actually just a wrapper for this function. 

`YFuncStats` holds the stat items as a list of `YFuncStat` objects. 

#### `add(path, type="ystat")`

This method loads the saved profile stats stored in file at `path`. 

`type` indicates the type of the saved profile stats.

Currently, only loading from `"ystat"` format is possible. `"ystat"` is the current yappi internal format.`


#### `save(path, type="ystat")`

This method saves the current profile stats to file at `path`. 

`type` indicates the target type that the profile stats will be saved in.

Can be either
[`"pstats"`](http://docs.python.org/3.3/library/profile.html?highlight=pstat#pstats.Stats.print_stats) or
[`"callgrind"`](http://kcachegrind.sourceforge.net/html/CallgrindFormat.html).

#### `print_all(out=sys.stdout)`

This method prints the current profile stats to `out`.

#### `sort(sort_type, sort_order="desc")`

This method sorts the current profile stats.

The `sort_type` must be one of the following:

- `ncall`
- `ttot`
- `tsub`
- `tavg`

`sort_order` must be either `desc` or `asc`

#### `clear()`

Clears the retrieved stats. 

Note that this only clears the current object's stat list. You need to explicitly call `yappi.clear_stats()` to clear the current profile's stats.

#### `empty()`

Returns a boolean indicating whether we have any stats available or not.

#### `strip_dirs()`

Strip the directory information from the results. Affects the child function stats too.

#### `debug_print()`

This method _debug_ prints the current profile stats to stdout. 

Debug print prints out callee functions and more detailed info than the _print_all()_ function call.
