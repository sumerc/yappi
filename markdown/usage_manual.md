# Usage Manual (v0.82)

A typical example on profiling with yappi, includes at least 3 lines of
code:

```python
import yappi


def a():
    for i in range(10000000): pass

yappi.start()

a()

yappi.get_func_stats().print_all()
yappi.get_thread_stats().print_all()
```

And the output of running above script:

```
Clock type: cpu
Ordered by: totaltime, desc

name                    ncall      tsub      ttot      tavg
deneme.py:35 a          1          0.296402  0.296402  0.296402

name           tid              ttot      scnt
_MainThread    6016             0.296402  1
```

**Let's inspect the results in detail.**

---

The first line:

```
Clock type: cpu
```

indicates the profiling timing stats shown are retrieved using the CPU clock.
That means the actual CPU time spent in the function is shown.

Yappi provides two modes of operation: CPU and Wall time profiling. You can change the
setting by a call to `yappi.set_clock_type()`.

Read [ClockTypes](./clock_types.md) for more.

---

Second is:

```
Ordered by: totaltime, desc
```

This shows the sort order and sort key of the
shown profiling stats. You can see the valid values for this here - [`YFuncStats.sort()`]().

---

Now we actually see the statistic of the function call `a()`:

```
name                    ncall      tsub      ttot      tavg
deneme.py:35 a          1          0.296402  0.296402  0.296402
```


Here is what each of these mean -

| *Title* | *Description*                                                        |
|---------|----------------------------------------------------------------------|
| name    | the full unique name of the called function.                         |
| ncall   | How many times this function is called.                              |
| tsub    | How much time this function has spent in total, subcalls excluded.   |
| ttot    | How much time this function has spent in total, subcalls included.   |
| tavg    | How much time this function has spent in average, subcalls included. |


---

The next lines shows the thread stats:

```
name           tid              ttot      scnt
_MainThread    6016             0.296402  1
```

Here is what each of these mean -


| *Title* | *Description*                                                                                     |
|---------|---------------------------------------------------------------------------------------------------|
| name    | The class name of the Thread. (This is the name of the class inherits the threading.Thread class) |
| tid     | The thread id.                                                                                    |
| ttot    | How much time this thread has spent in total.                                                     |
| scnt    | How many times this thread is scheduled.                                                          |
