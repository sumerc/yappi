# Profiling Coroutines

Yappi is a deterministic profiler. This means it works by hooking into several function call/leave events as defined
[here](https://docs.python.org/2/library/sys.html#sys.setprofile) and calculates all metrics according to these. However.
the coroutine profiling problem defined below applies to nearly all of the profilers in the wild, including cProfile and the 
statistical profilers.

The main issue with coroutines is that, under the hood when a coroutine `yield`s or in other words context switches,
Yappi receives a `return` event just like we exit from the function. That means the time spent while the coroutine
is in `yield` state does not get accumulated to the output. This is a problem especially for walltime as in wall time you
want to see whole time spent in that function or coroutine. Another problem is call count. You see every time a coroutine
`yield`s, call count gets incremented since it is a regular function exit.

Let's profile below application via different profilers and examine the output:

```python
def burn_cpu(secs):
    t0 = time.process_time()
    elapsed = 0
    while (elapsed <= secs):
        for _ in range(1000):
            pass
        elapsed = time.process_time() - t0


async def burn_async_io(secs):
    await asyncio.sleep(secs)


def burn_io(secs):
    time.sleep(secs)


async def foo():
    burn_cpu(1.0)
    await burn_async_io(1.0)
    burn_io(1.0)
    await burn_async_io(1.0)

asyncio.run(foo)
```

Here is the output of above in cProfile:

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        4    0.000    0.000    0.000    0.000 cprofile_asyncio.py:14(burn_async_io)
        1    0.000    0.000    1.001    1.001 cprofile_asyncio.py:18(burn_io)
        3    0.000    0.000    2.002    0.667 cprofile_asyncio.py:22(foo)
        1    0.947    0.947    1.000    1.000 cprofile_asyncio.py:5(burn_cpu)
```

You can see `foo` seems to be called 3 times as it has context switched 2 times with `await` operations.
And you can also see `cumtime` is incorrect, the time spent in `await` instruction does not get accumulated.

Now let's profile same application via a statistical profiler, pyinstrument:

```
pyinstrument:
4.016 <module>  cprofile_asyncio.py:1
└─ 4.005 run  asyncio/runners.py:8
      [7 frames hidden]  asyncio, selectors
         2.003 select  selectors.py:451
         2.002 _run  asyncio/events.py:86
         └─ 2.002 foo  cprofile_asyncio.py:22
            ├─ 1.001 burn_io  cprofile_asyncio.py:18
            └─ 1.001 burn_cpu  cprofile_asyncio.py:5
```

Again: the time spent in `await` instructions does not get accumulated. In fact, statistical profilers 
have hard time calculating correct walltime spent in any kind of scenario(not just async. code) because
they are only looking for stack frames at specific intervals and they have no way of knowing what happened
between the measurement intervals. They are fundamentally different approach to profiling and I just wanted
to show that they are not also working for our case that is all.

With v1.2, Yappi corrects above issues with coroutine profiling. Under the hood, it differentiates the `yield` from real function exit and
if wall time is selected as the clock_type it will accumulate the time and corrects the call count metric.

Let's see the output in Yappi v1.2 for above application:

```
profile_asyncio.py:25 foo             1      0.000044  4.004661  4.004661
profile_asyncio.py:17 burn_async_io   2      0.000041  2.003238  1.001619
profile_asyncio.py:21 burn_io         1      0.000019  1.001135  1.001135
profile_asyncio.py:8 burn_cpu         1      0.935974  1.000244  1.000244
```

You can see that `foo` spent nearly 4 secs just like expected with a call count of 1.
And you can also see the other functions are also calculated correctly, too. `burn_cpu`
does have `tsub` nearly equal to `ttot` which is correct. 

