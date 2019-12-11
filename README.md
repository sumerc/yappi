<p align="center">
    <img src="https://github.com/sumerc/yappi/blob/coroutine-profiling/Misc/logo.png" alt="yappi">
</p>

<h1 align="center">Yappi</h1>
<p align="center">
    Yet Another Python Profiler, but this time <b>thread&coroutine</b> aware.
</p>

<p align="center">
    <img src="https://www.travis-ci.org/sumerc/yappi.svg?branch=master">
    <img src="https://img.shields.io/pypi/v/yappi.svg">
    <img src="https://img.shields.io/pypi/dw/yappi.svg">
    <img src="https://img.shields.io/pypi/pyversions/yappi.svg">
    <img src="https://img.shields.io/github/last-commit/sumerc/yappi.svg">
    <img src="https://img.shields.io/github/license/sumerc/yappi.svg">
</p>

## Highlights

- **Fast**: Yappi is fast. It is completely written in C and lots of love&care went into making it fast.
- **Unique**: Yappi supports multithreaded and [asyncronous code](https://github.com/sumerc/yappi/blob/master/doc/coroutine_profiling.md) profiling. Tagging/filtering multiple profiler results has interesting [use cases](https://github.com/sumerc/yappi/blob/master/doc/api.md#set_tag_callback).
- **Intuitive**: Profiler can be started/stopped and results can be obtained from any time and any thread.
- **Standarts Complaint**: Profiler results can be saved in [callgrind](http://valgrind.org/docs/manual/cl-format.html) or [pstat](http://docs.python.org/3.4/library/profile.html#pstats.Stats) formats.
- **Rich in Feature set**: Profiler results can show either [Wall Time](https://en.wikipedia.org/wiki/Elapsed_real_time) or actual [CPU Time](http://en.wikipedia.org/wiki/CPU_time) and can be aggregated from different sessions. Various flags are defined for filtering and sorting profiler results.
- **Robust**: Yappi is out in wild for more than *10 years* with lots of production usage.

## Motivation

CPython standard distribution comes with three deterministic profilers. `cProfile`, `Profile` and `hotshot`. `cProfile` is implemented as a C module based on `lsprof`, `Profile` is in pure Python and `hotshot` can be seen as a small subset of a cProfile. The major issue is that all of these profilers lack support for multi-threaded programs and CPU time.

If you want to profile a  multi-threaded application, you must give an entry point to these profilers and then maybe merge the outputs. None of these profilers are designed to work on long-running multi-threaded applications. It is also not possible to profile an application that start/stop/retrieve traces on the fly with these profilers. 

Now fast forwarding to 2019: With the latest improvements on `asyncio` library and asyncronous frameworks, most of the current profilers lacks the ability to show correct wall/cpu time or even call count information per-coroutine. Thus we need a different kind of approach to profile asyncronous code. Yappi, with v1.2 introduces the concept of `coroutine profiling`. With `coroutine-profiling`, you should be able to profile correct wall/cpu time and callcount of your coroutine. (including the time spent in context switches, too). You can see details [here](https://github.com/sumerc/yappi/blob/master/doc/coroutine_profiling.md).


## Installation

Can be installed via PyPI

```
$ pip install yappi
```

OR from the source directly.

```
$ pip install git+https://github.com/sumerc/yappi#egg=yappi
```

## Documentation

- [Introduction](https://github.com/sumerc/yappi/blob/master/doc/introduction.md)
- [Clock Types](https://github.com/sumerc/yappi/blob/master/doc/clock_types.md)
- [API](https://github.com/sumerc/yappi/blob/master/doc/api.md)

  Note: Yes. I know I should be moving docs to readthedocs.io. Stay tuned!


## Limitations:
* Threads must be derived from "threading" module's Thread object.

## Related Talks

  Special thanks to A.Jesse Jiryu Davis:
- [Python Performance Profiling: The Guts And The Glory (PyCon 2015)](https://www.youtube.com/watch?v=4uJWWXYHxaM)

## PyCharm Integration

Yappi is the default profiler in `PyCharm`. If you have Yappi installed, `PyCharm` will use it. See [the official](https://www.jetbrains.com/help/pycharm/profiler.html) documentation for more details.

