![Logo](https://camo.githubusercontent.com/628c5a0da5ce146f500b1ee43af6dcca3f4a6023/68747470733a2f2f692e696d6775722e636f6d2f78786d67476d6e2e706e67)
# Yappi
**Y**et **A**nother **P**ython **P**rof**i**ler, but this time thread and coroutine aware.

[![Build Status](https://www.travis-ci.org/sumerc/yappi.svg?branch=master)](https://www.travis-ci.org/sumerc/yappi)
![](https://img.shields.io/pypi/v/yappi.svg)
![](https://img.shields.io/pypi/dw/yappi.svg)
![](https://img.shields.io/pypi/pyversions/yappi.svg)
![](https://img.shields.io/github/last-commit/sumerc/yappi.svg)
![](https://img.shields.io/github/license/sumerc/yappi.svg)


## Motivation

CPython standard distribution comes with three deterministic profilers. `cProfile`, `Profile` and `hotshot`. `cProfile` is implemented as a C module based on `lsprof`, `Profile` is in pure Python and `hotshot` can be seen as a small subset of a cProfile. 

*The major issue is that all of these profilers lack support for multi-threaded programs and CPU time.*

If you want to profile a  multi-threaded application, you must give an entry point to these profilers and then maybe merge the outputs. None of these profilers are designed to work on long-running multi-threaded applications. It is also not possible to profile an application that start/stop/retrieve traces on the fly with these profilers. 

Now fast forwarding to 2019: With the latest improvements on `asyncio` library and asyncronous frameworks, most of the current profilers lacks the ability to show correct wall/cpu time or even call count information per-coroutine. Thus we need a different kind of approach to profile asyncronous code. Yappi, with v1.2 introduces the concept of `coroutine profiling`. With `coroutine-profiling`, you should be able to profile correct wall/cpu time and callcount of your coroutine. (including the time spent in context switches, too). You can see details [here](doc/coroutine_profiling.md).


## Highlights
- Correct function stats for [coroutines](https://docs.python.org/3/library/asyncio-task.html#coroutines). See [details](https://github.com/sumerc/yappi/blob/master/doc/coroutine_profiling.md). (New in 1.2)
- Tagging/filtering multiple profiler stats. See [details](https://github.com/sumerc/yappi/blob/master/doc/api.md#set_tag_callback). (New in 1.2)
- Per-thread function stats can be obtained
- Profiler can be started/stopped at any time from any thread in the application.
- Profiler traces can be obtained from any thread at any time.
- Profiler traces can show actual [CPU Time](http://en.wikipedia.org/wiki/CPU_time) used instead of Wall time.
- Profiler overhead is minimal since Yappi is completely implemented in C.

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

## Features
- Correct function stats for coroutines. See [details](https://github.com/sumerc/yappi/blob/master/doc/coroutine_profiling.md) here. (New in 1.2)
- Tagging/filtering multiple profiler stats. See [details](https://github.com/sumerc/yappi/blob/master/doc/api.md#set_tag_callback). (New in 1.2)
- Profiler results can be saved in [callgrind](http://valgrind.org/docs/manual/cl-format.html) or [pstat](http://docs.python.org/3.4/library/profile.html#pstats.Stats) formats. 
- Profiler results can be merged from different sessions on-the-fly.
- Profiler results can be easily converted to pstats.
- Profiling of multithreaded Python applications transparently.
- Supports profiling per-thread [CPU time](http://en.wikipedia.org/wiki/CPU_time)
- Profiler can be started from any thread at any time.
- Ability to get traces at any time without even stopping the profiler.
- Various flags to arrange/sort profiler results.
- Supports Python >= 2.7.x

## Limitations:
* Threads must be derived from "threading" module's Thread object.

## Talks

- [Python Performance Profiling: The Guts And The Glory (PyCon APAC 2014)](https://www.youtube.com/watch?v=BOKcZjI5zME)
- [Python Performance Profiling: The Guts And The Glory (PyCon 2015)](https://www.youtube.com/watch?v=4uJWWXYHxaM)
- [Python Performance Profiling: The Guts And The Glory (PyGotham 2016)](https://www.youtube.com/watch?v=EJ87Kfzvnbs)

## PyCharm Integration

Yappi is the default profiler in `PyCharm`. If you have Yappi installed, `PyCharm` will use it. See [the official](https://www.jetbrains.com/help/pycharm/profiler.html) documentation for more details.

