1.  summary Why we implemented yet another python profiler and some
    techinal details.

Motivation:
===========

\_CPython\_ standart distribution is coming with three profilers.
\_cProfile\_, \_Profile\_ and \_hotshot\_. \_cProfile\_ module is
implemented as a C module based on \_lsprof\_, \_Profile\_ is in pure
Python and the hotshot can be seen as a small subset of a cProfile. The
motivation to implement a new profiler is that all of these profilers
lacks the support of multi-threaded programs. If you want to profile a
multi-threaded application, you must give an entry point to these
profilers and then maybe merge the outputs. None of these profilers is
designed to work on long-running multi-threaded application. While
implementing a game server, it turns out that is is impossible to
profile an application retrieve the statistics then stop and then start
later on on the fly(without affecting the profiled application). With
the experience of implementing a game server in Python, we have
identified most of the problems, tricky parts regarding profiler usage
and so, we have come up with simple but powerful requirements.

Requirements:
=============

` * Profiler should be started/stopped at any time from any thread in the application.`\
` * Profile statistics should be obtained from any thread at any time.`\
` * Profile statistics will be calculated from *per-thread CPU time*.(new in v0.62)`\
` * `“`Profiler`` ``pollution`”`(effect on the application run-time) should be very minimal.`\
` `

Limitations:
============

` * Threads must be derived from `“`threading`”` module's Thread object.`\
` * Latest version of Yappi supports Python 2.6.x <= x <= Python.3.4`
