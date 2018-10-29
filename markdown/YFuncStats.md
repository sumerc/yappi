1.  summary yappi.YFuncStats

class YFuncStats (v0.82)
========================

<font face='Courier New'>

<b><i>class</i></b> yappi.<b>YFuncStats</b>

<b>get()</b>

`   This method retrieves the current profiling stats.      yappi.get_func_stats() is actually just a wrapper for this function. YFuncStats holds the stat items as a list of _YFuncStat_ object. `

`   A _YFuncStat_ object holds the following information:`

|| \*Key\* || \*Description\* || || index || A unique number for the
stat || || module || Module name of the executed function || || lineno
|| Line number of the executed function || || name || Name of the
executed function || || full\_name || module:lineno name - unique full
name of the executed function || || ncall || number of times the
executed function is called. || || nactualcall || number of times the
executed function is called, excluding the recursive calls. || ||
builtin|| boolean flag showing if the executed function is a builtin ||
|| ttot || total time spent in the executed function. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret this value correctly. || || tsub || total time spent in the
executed function, excluding subcalls. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret this value correctly. || || tavg || per-call average total
time spent in the executed function. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret this value correctly. || || children || list of functions
called from the executed function. See
[YChildFuncStats](https://code.google.com/p/yappi/wiki/YChildFuncStats_v082)
object ||

<b>add(path, type=“ystat”)</b>

`   This method loads the saved profile stats stored in file `<i>“`path`”</i>`. `<i>“`type`”</i>` indicates the type of the saved profile stats. `\
`   `\
`   The following are the load formats currently available:`

|| \*Format\* || || ystat ||

<b>save(path, type=“ystat”)</b>

`   This method saves the current profile stats to `<i>“`path`”</i>`. `<i>“`type`”</i>` indicates the target type that the profile stats will be saved in. Currently only loading from `<i>“`ystat`”</i>` format is possible. `<i>“`ystat`”</i>` is the current yappi internal format.`

`   The following are the save formats currently available:`

|| \*Format\* || || ystat || ||
[pstats](http://docs.python.org/3.3/library/profile.html?highlight=pstat#pstats.Stats.print_stats)
|| ||
[callgrind](http://kcachegrind.sourceforge.net/html/CallgrindFormat.html)
||

<b>print\_all(out=sys.stdout)</b>

`   This method prints the current profile stats to `<i>“`out`”</i>` which is  `<i>“`stdout`”</i>` by default. `

<b>sort(sort\_type, sort\_order=“desc”)</b>

`   This method sorts the current profile stats according to the  `<i>“`sort_type`”</i>` param. `

`   The following are the valid `<i>“`sort_type`”</i>` params:`

|| \*Sort Types\* || || name || || callcount/ncall || || totaltime/ttot
|| || subtime/tsub || || avgtime/tavg ||

`  The following are the valid `<i>“`sort_order`”</i>` params:`

|| \*Sort Orders\* || || descending/desc || || ascending/asc ||

<b>clear()</b>

`   Clears the retrieved stats. Note that this only clears the current object's stat list. You need to explicitly call _yappi.clear_stats()_ to clear the current profile stats.`

<b>empty()</b>

`   Returns a boolean indicating whether we have any stats available or not. `

<b>strip\_dirs()</b>

`   Strip the directory information from the results. Affects the child function stats, too.`

<b>debug\_print()</b>

`   This method _debug_ prints the current profile stats to `<i>“`stdout`”`. Debug print prints out callee functions and more detailed info than the _print_all()_ function call.`</i>` `

</font>
