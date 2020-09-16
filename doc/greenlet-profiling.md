# Profiling Greenlets

Yappi now supports profiling [greenlets](https://greenlet.readthedocs.io/en/latest/)!

How do you use it?
- [profile basic greenlet applications](#profile-simple-greenlets)
- [profile gevent applications](#profile-gevent-applications)

## Profile simple greenlets

### Basic Usage

Here's an example of profiling a simple greenlet based application which runs two greenlets

```python
import yappi
from greenlet import greenlet
import time

## Application logic

def burn_cpu(secs):
    t0 = time.process_time()
    elapsed = 0
    while (elapsed <= secs):
        for _ in range(1000):
            pass
        elapsed = time.process_time() - t0

class GreenletA(greenlet):
    def run(self):
        burn_cpu(0.1)

class GreenletB(greenlet):
    def run(self):
        burn_cpu(0.2)

# Running the profiler:

# Step 1: Configure the profiler to work with greenlets

yappi.set_context_backend("greenlet")
yappi.set_clock_type("cpu")

# Step 2: Run the profiler and stop it

yappi.start()

a = GreenletA()
b = GreenletB()

a.switch()
b.switch()

yappi.stop()

# Step 3: View results

print("## Function stats:")
yappi.get_func_stats().print_all()

print("\n## Greenlet stats:")
yappi.get_greenlet_stats().print_all()
```

Sample Output:

```
## Function stats:

Clock type: CPU
Ordered by: totaltime, desc

name                                  ncall  tsub      ttot      tavg
test.py:7 burn_cpu                    2      0.255467  0.300078  0.150039
test.py:20 GreenletB.run              1      0.000009  0.200057  0.200057
test.py:16 GreenletA.run              1      0.000008  0.100038  0.100038

## Greenlet stats:

name           id     ttot      scnt
GreenletB      3      0.200074  1
GreenletA      2      0.100051  1
greenlet       1      0.000076  3
```

The meaning of each column and table is explained here - [Introduction](https://github.com/sumerc/yappi/blob/master/doc/introduction.md)

## Profile gevent applications

With support for greenlets, you can now profile popular async frameworks built on top of greenlets like Gevents.

### Basic Usage

```python
import yappi
from gevent import Greenlet
import time

## Application logic

def burn_cpu(secs):
    t0 = time.process_time()
    elapsed = 0
    while (elapsed <= secs):
        for _ in range(1000):
            pass
        elapsed = time.process_time() - t0

class GreenletA(Greenlet):
    def _run(self):
        burn_cpu(0.1)

class GreenletB(Greenlet):
    def _run(self):
        burn_cpu(0.2)

# Running the profiler:

# Step 1: Configure the profiler to work with greenlets

yappi.set_context_backend("greenlet")
yappi.set_clock_type("cpu")

# Step 2: Run the profiler and stop it

yappi.start()

a = GreenletA()
b = GreenletB()

a.start()
b.start()
a.get()
b.get()

yappi.stop()

# Step 3: View results

print("## Function stats:")
yappi.get_func_stats().print_all()

print("\n## Greenlet stats:")
yappi.get_greenlet_stats().print_all()
```

Sample output:
```
## Function stats:

Clock type: CPU
Ordered by: totaltime, desc

name                                  ncall  tsub      ttot      tavg
tests/test_random.py:7 burn_cpu       2      0.257554  0.300067  0.150033
..s/test_random.py:20 GreenletB._run  1      0.000007  0.200025  0.200025
..s/test_random.py:16 GreenletA._run  1      0.000009  0.100058  0.100058
..
.. More function stats
..

## Greenlet stats:

name           id     ttot      scnt
GreenletB      4      0.200048  1
GreenletA      3      0.100075  1
greenlet       1      0.006496  2
Hub            2      0.000212  1
```

### With 'threading' monkey patched

When the threading module is monkey patched, `threading.Thread` is used to spawn greenlets instead
of `gevent.Greenlet`. Since yappi reports the name of each greenlet class by default, the user must
inform yappi to retrieve the class name from the `threading` library instead. Yappi provides
`set_context_name_callback` to do so. See below for an example:

```python
from gevent import monkey
monkey.patch_all()

import yappi
import threading
import gevent
import time

## Application logic

def burn_cpu(secs):
    t0 = time.process_time()
    elapsed = 0
    while (elapsed <= secs):
        for _ in range(1000):
            pass
        elapsed = time.process_time() - t0

class ThreadA(threading.Thread):
    def run(self):
        burn_cpu(0.1)

class ThreadB(threading.Thread):
    def run(self):
        burn_cpu(0.2)

# Running the profiler:

# Step 1: Configure the profiler to work with greenlets
yappi.set_context_backend("greenlet")
yappi.set_clock_type("cpu")

# Step 2: Configure the system to capture thread names correctly
def _ctx_name_callback():
    curr_gl = gevent.getcurrent()
    if curr_gl is gevent.get_hub():
        return curr_gl.__class__.__name__
    # yappi._ctx_name_callback returns the name of the thread
    # class
    return yappi._ctx_name_callback()

yappi.set_context_name_callback(_ctx_name_callback)

# Step 3: Run the profiler and stop it
yappi.start()

a = ThreadA()
b = ThreadB()

a.start()
b.start()
a.join()
b.join()

yappi.stop()

# Step 4: View results

print("## Function stats:")
yappi.get_func_stats().print_all()

print("\n## Greenlet stats:")
yappi.get_greenlet_stats().print_all()
```

Sample Output:
```
## Function stats:

Clock type: CPU
Ordered by: totaltime, desc

name                                  ncall  tsub      ttot      tavg
tests/test_random.py:11 burn_cpu      2      0.255339  0.300063  0.150031
..hreading.py:870 ThreadB._bootstrap  1      0.000011  0.200229  0.200229
..ng.py:901 ThreadB._bootstrap_inner  1      0.000059  0.200218  0.200218
tests/test_random.py:24 ThreadB.run   1      0.000010  0.200042  0.200042
..hreading.py:870 ThreadA._bootstrap  1      0.000012  0.100218  0.100218
..
.. More function stats
..

## Greenlet stats:

name           id     ttot      scnt
ThreadB        4      0.200243  1
ThreadA        3      0.100228  1
_MainThread    1      0.000875  4
Hub            2      0.000182  3
```


### Limitations in gevent profiling

Gevent allows users to run functions on a pool of native threads via [ThreadPool](http://www.gevent.org/api/gevent.threadpool.html). All threads spawned as part of this pool cannot be tracked by yappi and so yappi cannot report stats for functions / greenlets running on them.