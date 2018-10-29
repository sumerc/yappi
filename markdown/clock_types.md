# Clock Types

Currently, yappi supports two basic clock types used for calculating the timing data:

- [CPU Clock](http://en.wikipedia.org/wiki/CPU_time)

    `yappi.set_clock_type("cpu")`

- [Wall Clock](http://en.wikipedia.org/wiki/Wall_time)

    `yappi.set_clock_type("wall")`

## Example

```python
import time

import yappi


def my_func():
    time.sleep(4.0)


yappi.start()

my_func()

yappi.get_func_stats().print_all()
```

It prints put following:

```
$ python test.py

Clock type: CPU
Ordered by: totaltime, desc

name                                  ncall  tsub      ttot      tavg
test.py:6 my_func                     1      0.000012  0.000061  0.000061
```

So, what happened? Why does tsub only show `0.000012`?

The answer is that yappi supports CPU clock by
default for timing calculations as can be seen in the output:

```
Clock type: cpu
```

`time.sleep()` is a blocking function
(which means it actually blocks the calling thread, thread usually sleeps in the OS queue),
but, since it instructs the CPU to "sleep", the CPU clock cannot accumulate any timing data for the function `my_func`.

There are however, very few CPU cycles involved before calling
`time.sleep()`; that level of precision is not shown.

Let's see what happens when change the clock type to to Wall Clock:

```python
import time

import yappi


def my_func():
    time.sleep(4.0)


yappi.set_clock_type("wall")
yappi.start()

my_func()

yappi.get_func_stats().print_all()
```

Output for above is:

```
$ python test.py

Clock type: WALL
Ordered by: totaltime, desc

name                                  ncall  tsub      ttot      tavg
test.py:6 my_func                     1      0.000007  4.004159  4.004159
```

So, as you can see, now `time.sleep()` blocking call gets into account.

---

Let's add a piece of code that actually burns CPU cycles:

```python
import yappi

import time


def my_func():
    for i in range(10000000):
        pass

yappi.set_clock_type("cpu")
yappi.start()

my_func()

yappi.get_func_stats().print_all()
```


When you run the above script, you get:

```
$ python test.py

Clock type: CPU
Ordered by: totaltime, desc

name                                  ncall  tsub      ttot      tavg
test.py:5 my_func                     1      0.178615  0.178615  0.178615
```

---

NOTE: The values actually may differ from computer to computer as
CPU clock rates may differ significantly. Yappi actually uses native OS
APIs to retrieve per-thread CPU time information. You can see
[timing.c](/timing.c) module in the repository for details.

---

It is up to you to decide with which mode of clock type you need to profile your application.
