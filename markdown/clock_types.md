1.  summary yappi clock types

Clock Types
===========

Currently, yappi supports two basic clock types used for calculating the
timing data:

` * `[`CPU`` ``Clock`](http://en.wikipedia.org/wiki/CPU_time)\
` * `[`Wall`` ``Clock`](http://en.wikipedia.org/wiki/Wall_time)

Clock types of yappi can be change via calls to
\_yappi.set\_clock\_type()\_ API call.

Let's explain the concept via an example as I believe it is the best way
to explain something:

Suppose following code:

It prints put following:

So, what happened? The answer is that yappi supports CPU clock by
default for timing calculations as can be seen in the output:

And as \_time.sleep()\_ is a blocking function(which means it actually
block the calling thread, thread usually sleeps in the OS queue), the
CPU clock cannot accumulate any timing data for the function a. In fact,
there may be some very few CPU cycles involved before actually calling
the \_time.sleep\_, however that level of precision is not shown at all.

Let's see what happens when change the clock\_type to Wall Clock:

Output for above is:

So, as can be seen, now \_time.sleep\_ blocking call gets into account.
Let's add a piece of code that actually burns CPU cycles:

When you run the above script, you actually get:

 Note that the values actually may differ from computer to computer as
CPU clock rates may differ significantly. Yappi actually uses native OS
APIs to retrieve per-thread CPU time information. You can see
\_timing.c\_ module in the repository for details.

So, briefly, it is up to you to decide with which mode of clock type you
need to profile your application.
