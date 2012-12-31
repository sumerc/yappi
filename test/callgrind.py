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
    #f1()
    frecursive(n-1)


class A:
    def b(self):
        f1()

def foo():
    pass
        
def main():
    f2()
    f3()

    frecursive(5)

    a = A()
    a.b()

def f(n):
    if n == 0 or n == 1:
        return
    f(0)
    f(1)
    if n == 2:
        return
    f(2)

if __name__ == '__main__':
    yappi.start()
    main()
    #foo()
    #f(5)
    #frecursive(5)
    yappi.stop()
    
    filename = 'callgrind.yappi'
    yappi.get_func_stats().save(filename, type='callgrind')
    test_print('\nWritten callgrind file to %s\n' % filename)
    yappi.get_func_stats().print_all()
    
    if sys.hexversion < 0x03000000:
        import cProfile
        cProfile.run('main()', 'fooprof')
        import pstats
        p = pstats.Stats('fooprof')
        #p.strip_dirs().sort_stats(-1).print_stats()
        from pyprof2calltree import convert
        convert('fooprof', 'callgrind.cprofile')