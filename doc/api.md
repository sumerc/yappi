# API reference

## Functions

#### `start(builtins=False, profile_threads=True)`

Starts profiling all threads in the current interpreter instance. 
This function can be called from any thread at any time. 

Resumes profiling if stop() is called previously.

`builtins` enables profiling of builtin functions.

`profile_threads` enables profiling of all threads. If this flag is true, all current threads and the ones that are generated
in the future will be profiled.

#### `stop()`

Stop the profiler.

Same profiling session might be resumed later by calling `start()`.

#### `clear_stats()`

Clears the profiler results. 

All results stay in memory unless application (all threads including the main thread) exits or `clear_stats()` is explicitly called.


#### `get_func_stats(tag=None, ctx_id=None, filter_callback=None)`

Returns the function stats as a list of [`YFuncStat`](#yfuncstat) object. As Yappi is a C extension, it catches the profile data in C API.
Thus, the profile data collected is buffered until `clear_stats` is called. `get_func_stats` function enumerates the underlying
buffered data and aggregates the information there. The functions that contain same index id will be aggregated in a single `YFuncStat`
object. So, if you want to select a specific `tag` or `ctx_id`, you need to select by providing them as arguments to `get_func_stats`.
Otherwise, data with different `tag`/`ctx_id` will be combined into one `YFuncStat` object. If you really would like to enumerate
buffered stats in raw, you can use an undocumented function: `_yappi.enum_func_stats(enum_callback, filter_dict)`. You can see
the usage in `get_func_stats` function.

---
**Note:**

Filtering `tag` and `ctx_id` are very fast compared to using `filter_callback` since the filtering is completely done on the C extension
with an internal hash table.

---


`tag` retrieves the `YFuncStat` objects having the same `tag` as specified.

`ctx_id` retrieves the `YFuncStat` objects having the same `ctx_id` as specified.

`filter_callback` is a callback which takes a `YFuncStat` object as an argument and returns a boolean value to indicate
to include or exclude it. As the object is directly passed to the `filter_callback` you can easily filter on any attribute
that `YFuncStat` has.

---
**Note:**

The `filter` dict is deprecated. Please do not use it anymore. We still support that for backward compatability but 
it is not recommended anymore.

---

An example demonstrating how `filter_callback` can be used to filter on a function name having `foo`:

```python
stats = yappi.get_func_stats(
    filter_callback=lambda x: x.name == 'foo'
).print_all()
```

There are handy functions that can be used with `filter_callback` to match multiple functions or modules easily.
See [func_matches](#func_matchesstat-funcs) and [module_matches](#module_matchesstat-modules).


#### `get_thread_stats()`

Returns the thread stats as a [`YThreadStat`](#ythreadstat) object.

#### `is_running()`

Returns a boolean indicating whether profiler is running or not.

#### `get_clock_type()`

Returns information about the underlying clock type Yappi should use to measure timing.

Read [Clock Types](./clock_types.md) for more information.

#### `set_clock_type(type)`

Sets the underlying clock type. `type` must be one of `"wall"` or `"cpu"`.

Read [Clock Types](./clock_types.md) for more information.

#### `func_matches(stat, funcs)`

This function returns `True` if the `stat`(`YStat`) object is in a given list of `funcs`(`callable`) list.
An example usage is when filtering stats based on actual function objects:

```python
def a():
    pass

def b():
    pass

...
stats = yappi.get_func_stats(
    filter_callback=lambda x: yappi.func_matches(x, [a, b])
)
```

---
**Note:**

Once a profile session is saved or loaded from a file, you cannot use
`func_matches` on the items as the mapping between the stats and the functions are
not serialized.

---

#### `module_matches(stat, modules)`

This function returns `True` if the `stat`(`YStat`) object is in a given list of `modules`(`ModuleType`) list.
An example usage is when filtering stats based on actual module objects:

```python
import collections
...
stats = yappi.get_func_stats(
    filter_callback=lambda x: yappi.module_matches(x, [collections])
)
```

---
**Note:**

Once a profile session is saved or loaded from a file, you cannot use
`func_matches` on the items as the mapping between the stats and the functions are
not serialized.

---

#### `set_ctx_id_callback(callback)`

`callback` is a simple callable with no arguments that returns an integer.
`callback` is called for every profile event to get the current context id of a running context. 

In Yappi terminology a `context` means a construct that has its own callstack. It defaults to uniquely identifying a threading.Thread object, but there might be some advanced cases for this one, like a different threading library is used. 

This is an internally used function, so please do not play with unless you have a good reason.

---
**Note:**

The context id callback can be called from the `threading.Thread` initialization code and thus can hold some related
locks in `threading` library(e.x: _active_limbo_lock). So, it is not safe to use threading APIs like `threading.current_thread()`
which can also use these locks and lead to deadlocks. However, it is safe to use `threading.local()` or global variables
using your own locks.

---

#### `set_tag_callback(callback)` _New in v1.2_

`callback` is a simple callable with no arguments that returns an integer.
`callback` is called for every profile event to get the current tag id of a running function. 

In Yappi, every profiled function is associated with a tag. By default, this tag is same for all stats collected. You can change this behavior and aggregate different function stat data in different tags.
This will give additional name-spacing on what kind of data to collect.

A recent use case for this functionality is aggregating of single request/response cycle in an ASGI application via `contextvar` module. See [here](https://github.com/sumerc/yappi/issues/21) for details. It can also be used for profiling multithreaded WSGI applications, too.

A simple example demonstrating on how it can be used to profile request/response cycles in a multithreaded WSGI application where every request/response is handled by a different thread. See [here](https://modwsgi.readthedocs.io/en/develop/user-guides/processes-and-threading.html#the-unix-worker-mpm) for more details.

```python
_req_counter = 0
tlocal = threading.local()

def _worker_tag_cbk():
    global _req_counter

    if not getattr(tlocal, '_request_id'):
        _req_counter += 1 # protect this with mutex
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

---
**Note:**

Relevant request id is held in a thread local storage and we simply increment the counter when we encounter a new thread.
Above code will aggregate all stats into a single tag for every function called from the same thread.

---

#### `yappi.get_mem_usage()`

Returns the internal memory usage of the profiler itself.

#### `convert2pstats(stats)`

Converts the internal stat type of Yappi (as returned by `YFuncStat.get()`) to a [`pstats`](https://docs.python.org/3/library/profile.html#module-pstats) object.

# Classes

## `YFuncStat`

This holds the stat items as a list of `YFuncStat` objects. 

| Attribute   	| Description                                                                     	|
|-------------	|---------------------------------------------------------------------------------	|
| name        	| name of the executed function                                                   	|
| module      	| module name of the executed function                                            	|
| lineno      	| line number of the executed function                                            	|
| ncall       	| number of times the executed function is called.                                	|
| nactualcall 	| number of times the executed function is called, excluding the recursive calls. 	|
| builtin     	| bool, indicating whether the executed function is a builtin                     	|
| ttot        	| total time spent in the executed function                                       	|
| tsub        	| total time spent in the executed function, excluding subcalls                   	|
| tavg        	| per-call average total time spent in the executed function.                     	|
| index       	| unique id for the YFuncStat object                                              	|
| children    	| list of [YChildFuncStat](#ychildfuncstat) objects                              	|
| ctx_id      	| id of the underlying context(thread)                                            	|
| ctx_name    	| name of the underlying context(thread)                                          	|
| full_name   	| unique full name of the executed function                                       	|
| tag         	| tag of the executed function. (set via `set_tag_callback`<br>)                  	|

#### `get()`

This method retrieves the current profiling stats.      

[`yappi.get_func_stats()`](#get_func_statstagnone-ctx_idnone-filter_callbacknone) is actually just a wrapper for this function. 

#### `add(path, type="ystat")`

This method loads the saved profile stats stored in file at `path`. 

`type` indicates the type of the saved profile stats.

Currently, only loading from `"ystat"` format is possible. `"ystat"` is the current Yappi internal format.`


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

Clears the stats.

---
**Note:**

This method only clears the current object. You need to explicitly call [`yappi.clear_stats()`](#clear_stats) to clear the current profile session stats.

---

#### `empty()`

Returns a boolean indicating whether we have any stats available or not.

#### `strip_dirs()`

Strip the directory information from the results. Affects the child function stats too.

#### `debug_print()`

This method _debug_ prints the current profile stats to stdout. 

Debug print prints out callee functions and more detailed info than the [`print_all()`](#print_alloutsysstdout-1) function call.

## `YThreadStat`

`YThreadStat` object has following attributes:

| Attribute   	| Description                                                                                    	|
|-------------	|------------------------------------------------------------------------------------------------	|
| name        	| class name of the current thread object which is derived from the `threading.Thread`<br> class 	|
| id          	| a unique id given by Yappi (ctx_id)                                                            	|
| tid         	| the real OS thread id                                                                          	|
| ttot        	| total time spent in the thread                                                                 	|
| sched_count 	| number of times this thread is scheduled.                                                      	|

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

---
**Note:**

This method only clears the current object. You need to explicitly call [`yappi.clear_stats()`](#clear_stats) to clear the current profile session stats.

---

#### `empty()`

Returns a `bool` indicating whether we have any stats available or not.

## `YChildFuncStat`

This holds a list of child functions called from the main executed function as a `YChildFuncStat` object. 

This class holds a list of `YChildFuncStat` objects.

For example, if `a` calls `b`, then `a.children` will hold `b` as a `YChildFuncStat` object.

`YChildFuncStat` object has following attributes:

| Attribute   	| Description                                                                     	|
|-------------	|---------------------------------------------------------------------------------	|
| name        	| name of the executed function                                                   	|
| module      	| module name of the executed function                                            	|
| lineno      	| line number of the executed function                                            	|
| ncall       	| number of times the executed function is called.                                	|
| nactualcall 	| number of times the executed function is called, excluding the recursive calls. 	|
| builtin     	| bool, indicating whether the executed function is a builtin                     	|
| ttot        	| total time spent in the executed function                                       	|
| tsub        	| total time spent in the executed function, excluding subcalls                   	|
| tavg        	| per-call average total time spent in the executed function.                     	|
| index       	| unique id for the YFuncStat object                                              	|
| full_name   	| unique full name of the executed function                                       	|
