1.  summary yappi Usage Manual

Usage Manual (v0.82)
====================

A typical example on profiling with yappi, includes at least 3 lines of
code:

And the output of running above script:

Let's inspect the results in detail. So, first line: This indicates the
profiling timing stats shown are retrieved using the CPU clock. That
means the actual CPU time spent in the function is shown. Yappi provides
two modes of operation: CPU and Wall time profiling. You can change the
setting by a call to \_yappi.set\_clock\_type()\_ API. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret different timing values correctly.

Second is: It is obvious. It shows the sort order and sort key of the
shown profiling stats. You can see the valid values for this in
\_YFuncStats().sort()\_ API.

Ok, now we actually see the statistic of the function a(): Let's explain
the fields in detail: || \*Title\* || \*Description\* || || name || the
full unique name of the called function. || || \#n || how many times
this function is called. || || tsub || how many time this function has
spent in total, subcalls excluded. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret this value correctly. || || ttot || how many time this
function has spent in total, subcalls included. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret this value correctly. || || tavg || how many time this
function has spent in average, subcalls included. See [Clock
Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082) to
interpret this value correctly. ||

The next lines shows the thread stats. So, let see: || \*Title\* ||
\*Description\* || || name || the class name of the Thread.(this is the
name of the class inherits the threading.Thread class) || || tid || the
thread id. || || ttot || how many time this thread has spent in total.
See [Clock Types](https://code.google.com/p/yappi/wiki/ClockTypes_v082)
to interpret this value correctly. || || scnt || how many times this
thread is scheduled. ||
