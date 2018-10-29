# Yappi
**Y**et **A**nother **P**ython **P**rof**i**ler, but this time support Multithread/CPU time profiling.

![Logo](https://i.imgur.com/xxmgGmn.png)

## Motivation

CPython standard distribution comes with three profilers. `cProfile`, `Profile` and `hotshot`. 
`cProfile` is implemented as a C module based on `lsprof`, `Profile` is in pure Python and 
`hotshot` can be seen as a small subset of a cProfile. 

*The major issue is that all of these profilers lack support for multi-threaded programs.*

If you want to profile a  multi-threaded application, you must give an entry point to these profilers and then maybe merge 
the outputs. None of these profilers are designed to work on long-running multi-threaded application. 

While implementing a game server, it turns out that is is impossible to profile an application 
retrieve the statistics then stop and then start later on on the fly (without affecting the profiled
application).

With the experience of implementing a game server in Python, we have identified most 
of the problems, tricky parts regarding profiler usage and so, we have come up with simple but 
powerful profiler for python.

## Guarantees

- Profiler can be started/stopped at any time from any thread in the application.
- Profile statistics can be obtained from any thread at any time.
- Profile statistics will be calculated from *per-thread CPU time*. (new in v0.62)
- “Profiler pollution” (effect on the application run-time) is very minimal.

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

- [Introduction](markdown/introduction.md)
- [API](markdown/api.md)

## Talks

- Python Performance Profiling: The Guts And The Glory
  [![Youtube link](https://img.youtube.com/vi/BOKcZjI5zME/0.jpg)](https://www.youtube.com/watch?v=BOKcZjI5zME)
  

## Features
- Profiler results can be saved in [callgrind](http://valgrind.org/docs/manual/cl-format.html) or [pstat](http://docs.python.org/3.4/library/profile.html#pstats.Stats) formats. (*new in 0.82*)
- Profiler results can be merged from different sessions on-the-fly. (*new in 0.82*)
- Profiler results can be easily converted to pstats. (*new in 0.82*)
- Profiling of multithreaded Python applications transparently.
- Supports profiling per-thread [CPU time](http://en.wikipedia.org/wiki/CPU_time) (*new in 0.62*)
- Profiler can be started from any thread at any time.
- Ability to get statistics at any time without even stopping the profiler.
- Various flags to arrange/sort profiler results.
- Supports Python 2.6.x <= x <= Python 3.4

## Limitations:
* Threads must be derived from "threading" module's Thread object.
* Latest version of Yappi supports 2.6 <= Python <= 3.4
