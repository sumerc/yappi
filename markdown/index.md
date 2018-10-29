Features (v0.82)
================

- Profiler results can be saved in [callgrind](http://valgrind.org/docs/manual/cl-format.html) or [pstat](http://docs.python.org/3.4/library/profile.html#pstats.Stats) formats. (*new in 0.82*)
- Profiler results can be merged from different sessions on-the-fly. (*new in 0.82*)
- Profiler results can be easily converted to pstats. (*new in 0.82*)
- Profiling of multithreaded Python applications transparently.
- Supports profiling per-thread [CPU time](http://en.wikipedia.org/wiki/CPU_time)(*new in 0.62*)
- Profiler can be started from any thread at any time.
- Ability to get statistics at any time without even stopping the profiler.
- Various flags to arrange/sort profiler results.
- Supports Python 2.6.x <= x <= Python 3.4`

Installation
============

Can be installed via PyPI

```
$ pip install yappi
```


or from the source directly.

```
$ pip install git+https://github.com/sumerc/yappi#egg=yappi
```
