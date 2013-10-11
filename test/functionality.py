import time
import yappi
import _yappi
import threading
from test_utils import assert_raises_exception, run_and_get_func_stats, test_passed, run_and_get_thread_stats,get_child_stat,test_start

CONTINUE = 1
STOP = 3

# try get_stats() before start
assert_raises_exception('yappi.get_stats()')

# try clear_stats() while running
assert_raises_exception('yappi.clear_stats()')

# trivial function timing check
def foo():
    for i in range(1000000):
        pass
    import time
    time.sleep(1.0)
    
stats = run_and_get_func_stats('foo()')
fs = stats.find_by_name('foo')
assert fs != None
assert fs.ttot < 1.0
assert fs.tsub < 1.0
assert fs.ncall == 1

test_passed("trivial timing function")

# try get_stats after clear_stats
test_start()
assert_raises_exception('yappi.get_stats()')
# try profiling a simple recursive function
def fib(n):
   if n > 1:
       return fib(n-1) + fib(n-2)
   else:
       return n

stats = run_and_get_func_stats('fib(22)')
fs = stats.find_by_name('fib')
assert fs.ncall == 57313
assert fs.ttot == fs.tsub
test_passed("recursive function #1 ")

test_start()
def bar():
    for i in range(1000000):pass
stats = run_and_get_func_stats('bar()')
stats.sort(sort_type="totaltime") 
prev_stat = stats[0] # sorted ascending TTOT
for stat in stats:
    assert stat.ttot <= prev_stat.ttot
    prev_stat = stat    
test_passed("basic stat filtering")
    
stats = run_and_get_thread_stats('bar()')
assert stats[0].sched_count != 0
assert stats[0].ttot >= 0.0
test_passed("basic thread stat functionality")

test_start()

_timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "d_1":12, "c_2":10, "a_3":5}
_yappi.set_timings(_timings)
    
def a(n):
    if n == STOP:
        return
    if n == CONTINUE + 1:
        d(n)
    else:
        b(n)    
def b(n):        
    c(n)    
def c(n):
    a(n+1)    
def d(n):
    c(n)    
stats = run_and_get_func_stats('a(CONTINUE)')
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
fsc = stats.find_by_name('c')
fsd = stats.find_by_name('d')
assert fsa.ncall == 3
assert fsa.nactualcall == 1
assert fsa.ttot == 20
assert fsa.tsub == 7
assert fsb.ttot == 19
assert fsb.tsub == 2
assert fsc.ttot == 17
assert fsc.tsub == 9
assert fsd.ttot == 12
assert fsd.tsub == 2
cfsca = get_child_stat(fsc, fsa)
assert cfsca.nactualcall == 0
assert cfsca.ncall == 2
assert cfsca.ttot == 13
assert cfsca.tsub == 6
test_passed("recursive function (abcadc)")

test_start()
_timings = {"d_1":9, "d_2":7, "d_3":3, "d_4":2}
_yappi.set_timings(_timings)
def d(n):
    if n == STOP:
        return
    d(n+1)
stats = run_and_get_func_stats('d(CONTINUE-1)')
fsd = stats.find_by_name('d')
assert fsd.ncall == 4
assert fsd.nactualcall == 1
assert fsd.ttot == 9
assert fsd.tsub == 9
cfsdd = get_child_stat(fsd, fsd)
assert cfsdd.ttot == 7
assert cfsdd.tsub == 7
assert cfsdd.ncall == 3
assert cfsdd.nactualcall == 0
test_passed("recursive function (aaaa)")

test_start()
_timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "b_2":11, "c_2":9, "a_3":6}
_yappi.set_timings(_timings)
    
def a(n):
    if n == STOP:
        return
    else:
        b(n)
def b(n):        
    c(n)    
def c(n):
    a(n+1)    

stats = run_and_get_func_stats('a(CONTINUE)')
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
fsc = stats.find_by_name('c')
assert fsa.ncall == 3
assert fsa.nactualcall == 1
assert fsa.ttot == 20
assert fsa.tsub == 9
assert fsb.ttot == 19
assert fsb.tsub == 4
assert fsc.ttot == 17
assert fsc.tsub == 7
cfsab = get_child_stat(fsa, fsb)
cfsbc = get_child_stat(fsb, fsc)
cfsca = get_child_stat(fsc, fsa)
assert cfsab.ttot == 19
assert cfsab.tsub == 4
assert cfsbc.ttot == 17
assert cfsbc.tsub == 7
assert cfsca.ttot == 13
assert cfsca.tsub == 8

#stats.debug_print()
test_passed("recursive function (abcabc)")

#TODO:
# abcbca
# aabccb
# abaa
# bbaa
# abbb
# aaab
# baba
# abcd

test_start()
_timings = {"a_1":6,"b_1":4}
_yappi.set_timings(_timings)

def a():
    b()
    yappi.stop()
    
def b():    
    time.sleep(0.2)

yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')

assert fsa.ncall == 1
assert fsa.nactualcall == 0
assert fsa.ttot == 0 # no call_leave called
assert fsa.tsub == 0 # no call_leave called
assert fsb.ttot == 4 
# fsb.tsub might differ as we use timings dict and builtins are not enabled. 

#stats.debug_print()
test_passed("stop in the middle")

test_start()
_timings = {"a_1":6,"b_1":5,"c_1":3}
_yappi.set_timings(_timings)

def a():
    b()
def b():
    c()
def c():
    pass
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
fsc = stats.find_by_name('c')
cfsab = get_child_stat(fsa, fsb)
cfsbc = get_child_stat(fsb, fsc)

assert fsa.ttot == 6
assert fsa.tsub == 1
assert fsb.ttot == 5
assert fsb.tsub == 2
assert fsc.ttot == 3
assert fsc.tsub == 3
assert cfsab.ttot == 5
assert cfsab.tsub == 2
assert cfsbc.ttot == 3
assert cfsbc.tsub == 3

test_passed("basic (abc)")

test_passed("FUNCTIONALITY TESTS")

