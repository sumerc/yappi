Features (v0.82)
================

` * Profiler results can be saved in `[`callgrind`](http://valgrind.org/docs/manual/cl-format.html)` and `[`pstat`](http://docs.python.org/3.4/library/profile.html#pstats.Stats)` formats. (*new in 0.82*) `\
` * Profiler results can be merged from different sessions on-the-fly. (*new in 0.82*)`\
` * Profiler results can be easily converted to pstats. (*new in 0.82*) `\
` * Profiling of multithreaded Python applications transparently. `\
` * Supports profiling per-thread `[`CPU`` ``time`](http://en.wikipedia.org/wiki/CPU_time)`(*new in 0.62*)`\
` * Profiler can be started from any thread at any time.`\
` * Ability to get statistics at any time without even stopping the profiler.`\
` * Various flags to arrange/sort profiler results.`\
` * Supports Python 2.6.x <= x <= Python 3.4`

Installation
============

Can be installed via \*easy\_install yappi\* , \*pip install yappi\* or
from the source directly.

Documentation:
==============

Please see [API reference
manual](http://code.google.com/p/yappi/wiki/apiyappi_v082). For how to
use the profiler and how to interpret statistics output, see [usage
reference manual](http://code.google.com/p/yappi/wiki/usageyappi_v082).
And finally, see [requirements and
techinal](http://code.google.com/p/yappi/wiki/whyyappi) section for why
we have implemented yet another python profiler and some technical info
about the internals.

Development
===========

Latest development sources can be found
\[<http://bitbucket.org/sumerc/yappi/%5D*>.

A Simple Example:
=================


