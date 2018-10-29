1.  summary yappi Reference Manual

\_\*Please note that current version of yappi (v0.82) is not compatible
with the older versions. Lots of existing API have been changed.\*\_

Reference Manual (v0.82)
========================

<font face='Courier New'> yappi.<b>start</b>(builtins=False,
profile\_threads=True)

`   Starts profiling all threads in the current interpreter instance. This function can be called from any thread at any time. Resumes profiling if stop() is called previously.`

`   Current parameters:`

|| \*Param\* || \*Description\* || || builtins || Profile builtin
functions used by standart Python modules. It is \_False\_ by
\_default\_. || || profile\_threads || Profile all of the threads if
'true', else, profile only the calling thread. ||

<font face='Courier New'> yappi.<b>stop</b>() </font>

`   Stops the currently running yappi instance. Same profiling session might be resumed later by calling start().`

<font face='Courier New'> yappi.<b>clear\_stats</b>() </font>

`   Clears the profiler results. The results stays in memory unless application(all threads including the main thread) exists or clear_stats() is called.`

<font face='Courier New'> yappi.<b>get\_func\_stats</b>() </font>

`   Returns the function stats as `[`YFuncStats`](https://code.google.com/p/yappi/wiki/YFuncStats_v082)`  object.`

<font face='Courier New'> yappi.<b>get\_thread\_stats</b>() </font>

`   Returns the thread stats as `[`YThreadStats`](https://code.google.com/p/yappi/wiki/YThreadStats_v082)`  object.`

<font face='Courier New'> yappi.<b>is\_running</b>() </font>

`   Returns a boolean indicating whether profiler is running or not.`

<font face='Courier New'> yappi.<b>get\_clock\_type</b>() </font>

`   Returns information about the underlying clock type Yappi uses to measure timing.`

<font face='Courier New'> yappi.<b>set\_clock\_type</b>(type) </font>

`   Sets the underlying clock type. _type_ can be following: `

|| \*Clock Type\* || \*Description\* || || Wall ||
[Details](http://en.wikipedia.org/wiki/Wall_time) || || CPU ||
[Details](http://en.wikipedia.org/wiki/CPU_time) ||

<font face='Courier New'> yappi.<b>get\_mem\_usage</b>() </font>

`   Returns the internal memory usage of the profiler itself.`

<font face='Courier New'> yappi.<b>convert2pstats</b>(stats) </font>

`   Converts the internal stat type of yappi(which is returned by a call to YFuncStats.get()) as `[`pstats`](http://docs.python.org/3.4/library/profile.html#module-pstats)` object.`

</font>
