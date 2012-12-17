#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import yappi
from test_utils import test_print

RI = range(300)
RJ = range(10000)

def f1(n=1):
    """Spend some time doing some computation. We can't use time.sleep here,
    as we want to burn real CPU cycles."""
    a = 0
    for k in range(n):
        for i in RI:
            for j in RJ:
                a += i*j % 23

def f2():
    f1()

def f3():
    f1()
    f1()
    f1()

def frecursive(n):
    if n == 0:
        return
    f1()
    frecursive(n-1)


class A:
    def b(self):
        f1()

def main():
    f2()
    f3()

    frecursive(5)

    a = A()
    a.b()


if __name__ == '__main__':
    yappi.start()
    main()
    yappi.stop()

    try:
        verbose = (sys.argv[1] == '-v')

        if verbose:
            test_print('\n\nSORTED BY SUB TIME')
            yappi.print_func_stats(sort_type=yappi.SORTTYPE_TSUB,
                                   limit=20)
            test_print('\n\nSORTED BY TOTAL TIME')
            yappi.print_func_stats(sort_type=yappi.SORTTYPE_TTOT,
                                   limit=20)
            test_print('\n\nTHREAD STATS')
            yappi.print_thread_stats()

    except IndexError:
        pass

    filename = 'callgrind.out'
    yappi.write_callgrind_stats(open(filename, 'w'))
    test_print('\nWritten callgrind file to %s\n' % filename)
