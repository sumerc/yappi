# API reference

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

#### `set_ctx_id_callback(callback)`

`callback` is a simple callable with no arguments that returns an integer.
`callback` is called for every profile event to get the current context id of a running context. 

In Yappi terminology a `context` means a construct that has its own callstack. It defaults to uniquely identifying a threading.Thread object, but there are some advanced cases for this one, like [here](https://github.com/ajdavis/GreenletProfiler) where you have application threads scheduled by a custom scheduler which does not have a OS thread equivalent. In those extreme cases, this function can be used.

#### `set_tag_callback(callback)` _New in v1.2_

`callback` is a simple callable with no arguments that returns an integer.
`callback` is called for every profile event to get the current tag id of a running function. 

In Yappi, every profiled function is associated with a tag. By default, this tag is same for all stats collected. You can change this behaviour and aggregate different function stat data in different tags.
This will give additional namespacing on what kind of data to collect.

A recent use case for this functionality is aggregating of single request/response cycle in an ASGI application via `contextvar` module. See [here](https://github.com/sumerc/yappi/issues/21) for details. It can also be used for profiling multithreaded WSGI applications, too.

A simple example demonstrating on how it can be used to profile request/response cycles in a multithreaded WSGI application where every request/response is handled by a different thread. See [here](https://modwsgi.readthedocs.io/en/develop/user-guides/processes-and-threading.html#the-unix-worker-mpm) for more details.

```python
_req_counter = 0

def _worker_tag_cbk():
    global _req_counter
    tlocal = threading.local()
    if not getattr(tlocal, '_request_id'):
        _req_counter += 1
        tlocal._request_id = _req_counter
    
    return tlocal._request_id


yappi.set_tag_callback(_worker_tag_cbk)
yappi.start()
...
# code that starts a server serving request with different threads
...
yappi.stop()

# get per-request/response cycle profiling info
for i in range(_req_counter):
    req_stats = yappi.get_func_stats(filter={'tag': i})
    req_stats.print_all()

```

Please note that, the relevant request id is held in a thread local storage and we simply increment the counter when we encounter a new thread.
Above code will aggregate all stats into a single tag for every function called from the same thread.

#### `get_func_stats(filter=None)`

Returns the function stats as a [`YFuncStat`](#yfuncstat) object.
filter parameter can be used to filter on YFuncStat attributes. You can use multiple filters at once in a single call and only those results are returned. If no filter is defined, all function stats are aggregated(function stats are held per-thread under the hood) and returned. 

One of the interesting features of this filter function is that you can get per-thread function call statistics only by providing the `ctx_id` of the thread you want to get results. Under the hood, yappi already holds the function stats by per-thread and upon request, it aggregates this data, when you provide a filter, it simply returns only that per-thread stats.

```python
threads = yappi.get_thread_stats()
for thread in threads:
    fstats = yappi.get_func_stats(filter={"ctx_id":thread.id})
```

You can also set custom tags for specific functions and aggregate those by filtering on tag

```python
fstats = yappi.get_func_stats(filter={"tag": my_custom_tag_id})
```

#### `get_thread_stats()`

Returns the thread stats as a [`YThreadStat`](#ythreadstat) object.

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

Converts the internal stat type of yappi (as returned by `YFuncStat.get()`) to a [`pstats`](https://docs.python.org/3/library/profile.html#module-pstats) object.

# Classes

## `YFuncStat`

This holds the stat items as a list of `YFuncStat` objects. 

| *Attribute*  | *Description*                                                                   |
|-------------|---------------------------------------------------------------------------------|
| `name`        | Name of the executed function                                                   |
| `module`      | Module name of the executed function                                            |
| `lineno`      | Line number of the executed function                                            |
| `ncall`       | number of times the executed function is called.                                |
| `nactualcall` | number of times the executed function is called, excluding the recursive calls. |
| `builtin`     | bool, indicating whether the executed function is a builtin                     |
| `ttot`        | total time spent in the executed function                                       |
| `tsub`        | total time spent in theexecuted function, excluding subcalls                    |
| `index`       | A unique number for the stat                                                    |
| `children`    | list of functionscalled from the executed function                              |
| `ctx_id`      | Id of the underlying context(thread)                                            |
| `tavg`        | per-call average total time spent in the executed function.                     |
| `full_name`   | unique full name of the executed function                                       |

#### `get()`

This method retrieves the current profiling stats.      

[`yappi.get_func_stats()`](#get_func_statsfilternone) is actually just a wrapper for this function. 


#### `add(path, type="ystat")`

This method loads the saved profile stats stored in file at `path`. 

`type` indicates the type of the saved profile stats.

Currently, only loading from `"ystat"` format is possible. `"ystat"` is the current yappi internal format.`


#### `save(path, type="ystat")`

This method saves the current profile stats to file at `path`. 

`type` indicates the target type that the profile stats will be saved in.

Can be either
[`"pstat"`](http://docs.python.org/3.3/library/profile.html?highlight=pstat#pstats.Stats.print_stats) or
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

`sort_order` must be either `"desc"` or `"asc"`

#### `clear()`

Clears the retrieved stats. 

Note that this only clears the current object's stat list. You need to explicitly call [`yappi.clear_stats()`](#clear_stats) to clear the current profile's stats.

#### `empty()`

Returns a boolean indicating whether we have any stats available or not.

#### `strip_dirs()`

Strip the directory information from the results. Affects the child function stats too.

#### `debug_print()`

This method _debug_ prints the current profile stats to stdout. 

Debug print prints out callee functions and more detailed info than the [`print_all()`](#print_alloutsysstdout) function call.

## `YThreadStat`

This holds the stat items as a list of `YThreadStat` object.

| *Attribute*  | *Description*                                                                   |
|-------------|---------------------------------------------------------------------------------|
| `id`        | thread id given by the OS                                                 |
| `name`      | class name of the current thread object which is derived from the `threading.Thread` class                                            |
| `ttot`      | total time spent in the last executed function                                        |
| `sched_count`       | number of times this thread is scheduled. |


#### `get()`

This method retrieves the current thread stats.     

[`yappi.get_thread_stats()`](#get_thread_stats) is actually just a wrapper for this function. 

#### `print_all(out=sys.stdout)`

 This method prints the current profile stats to the file `out`.

#### `sort(sort_type, sort_order="desc")`

This method sorts the current profile stats.

`sort_type` must be either `"ttot"` or `"scnt"`

`sort_order` must be either `"desc"` or `"asc"`


#### `clear()`

Clears the retrieved stats. 

Note that this only clears the current object's stat list. 
You need to explicitly call [`yappi.clear_stats()`](#clear_stats) to clear the current profile stats.

#### `empty()`

Returns a `bool` indicating whether we have any stats available or not.

## `YChildFuncStat`

This holds a list of child functions called from the main executed function as a `YChildFuncStat` object. 

This class holds a list of `YChildFuncStat` objects.

For example, if `a` calls `b`, then `a.children` will hold `b` as a `YChildFuncStat` object.

Holds the same attributes and methods as [`YFuncStat`](#yfuncstat).
