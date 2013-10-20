import time
import yappi
import _yappi
import threading
from test_utils import assert_raises_exception, run_and_get_func_stats, test_end, run_and_get_thread_stats,get_child_stat,test_start

"""
TODO: 
 - ctx stat correctness, 
 - some stat save/load test, 
 - linux set_test_timings does not work correctly. floating arithmetic differs a bit
   we shall not rely on floating point arithmetic on different OSes(1.0 / tickfactor())
   make multiplying by tickfactor() a separate function.
"""
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

test_end("trivial timing function")

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
test_end("recursive function #1 ")

test_start()
def bar():
    for i in range(1000000):pass
stats = run_and_get_func_stats('bar()')
stats.sort(sort_type="totaltime") 
prev_stat = stats[0] # sorted ascending TTOT
for stat in stats:
    assert stat.ttot <= prev_stat.ttot
    prev_stat = stat    
test_end("basic stat filtering")
    
stats = run_and_get_thread_stats('bar()')
assert stats[0].sched_count != 0
assert stats[0].ttot >= 0.0
test_end("basic thread stat functionality")

test_start()
yappi.clear_stats()
test_end("clear_stats without stats")

test_start()
yappi.start()
yappi.set_clock_type('cpu') # return silently if same clock_type
assert_raises_exception('yappi.set_clock_type("wall")')
test_end("set_clock_type while running")

test_start()
_timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "d_1":12, "c_2":10, "a_3":5}
_yappi.set_test_timings(_timings)
    
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
test_end("recursive function (abcadc)")

test_start()
_timings = {"d_1":9, "d_2":7, "d_3":3, "d_4":2}
_yappi.set_test_timings(_timings)
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
test_end("recursive function (aaaa)")

test_start()
_timings = {"a_1":20,"b_1":19,"c_1":17, "a_2":13, "b_2":11, "c_2":9, "a_3":6}
_yappi.set_test_timings(_timings)
    
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
test_end("recursive function (abcabc)")

test_start()
_timings = {"a_1":6,"b_1":5,"c_1":3, "d_1":1}
_yappi.set_test_timings(_timings)

def a():
    b()
def b():
    c()
def c():
    d()
def d():
    pass
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
fsc = stats.find_by_name('c')
fsd = stats.find_by_name('d')
cfsab = get_child_stat(fsa, fsb)
cfsbc = get_child_stat(fsb, fsc)
cfscd = get_child_stat(fsc, fsd)

assert fsa.ttot == 6
assert fsa.tsub == 1
assert fsb.ttot == 5
assert fsb.tsub == 2
assert fsc.ttot == 3
assert fsc.tsub == 2
assert fsd.ttot == 1
assert fsd.tsub == 1
assert cfsab.ttot == 5
assert cfsab.tsub == 2
assert cfsbc.ttot == 3
assert cfsbc.tsub == 2
assert cfscd.ttot == 1
assert cfscd.tsub == 1
#stats.debug_print()
test_end("basic (abcd)")

test_start()
_timings = {"a_1":10,"b_1":9,"c_1":7,"b_2":4,"c_2":2,"a_2":1}
_yappi.set_test_timings(_timings)
ncall = 1
def a():
    global ncall
    if ncall == 1:
        b()
    else:
        return
def b():
    c()
def c():
    global ncall
    if ncall == 1:
        ncall += 1
        b()
    else:
        a()
        
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
fsc = stats.find_by_name('c')
cfsab = get_child_stat(fsa, fsb)
cfsbc = get_child_stat(fsb, fsc)
cfsca = get_child_stat(fsc, fsa)
assert fsa.ttot == 10
assert fsa.tsub == 2
assert fsb.ttot == 9
assert fsb.tsub == 4
assert fsc.ttot == 7
assert fsc.tsub == 4
assert cfsab.ttot == 9
assert cfsab.tsub == 2
assert cfsbc.ttot == 7
assert cfsbc.tsub == 4
assert cfsca.ttot == 1
assert cfsca.tsub == 1
assert cfsca.ncall == 1
assert cfsca.nactualcall == 0
#stats.debug_print()
test_end("recursive function (abcbca)")

test_start()
_timings = {"a_1":13,"a_2":11,"b_1":9,"c_1":5,"c_2":3,"b_2":1}
_yappi.set_test_timings(_timings)
ncall = 1
def a():
    global ncall
    if ncall == 1:
        ncall += 1
        a()
    else:
        b()
def b():
    global ncall
    if ncall == 3:
        return
    else:
        c()
def c():
    global ncall
    if ncall == 2:
        ncall += 1
        c()
    else:
        b()
        
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
fsc = stats.find_by_name('c')
cfsaa = get_child_stat(fsa, fsa)
cfsab = get_child_stat(fsa, fsb)
cfsbc = get_child_stat(fsb, fsc)
cfscc = get_child_stat(fsc, fsc)
cfscb = get_child_stat(fsc, fsb)
assert fsb.ttot == 9
assert fsb.tsub == 5
assert cfsbc.ttot == 5
assert cfsbc.tsub == 2
assert fsa.ttot == 13
assert fsa.tsub == 4
assert cfsab.ttot == 9
assert cfsab.tsub == 4
assert cfsaa.ttot == 11
assert cfsaa.tsub == 2
assert fsc.ttot == 5
assert fsc.tsub == 4
#stats.debug_print()
test_end("recursive function (aabccb)")

test_start()
_timings = {"a_1":13,"b_1":10,"a_2":9,"a_3":5}
_yappi.set_test_timings(_timings)

ncall = 1
def a():
    global ncall
    if ncall == 1:
        b()
    elif ncall == 2:
        ncall += 1
        a()
    else:
        return
def b():
    global ncall
    ncall += 1
    a()
    
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
cfsaa = get_child_stat(fsa, fsa)
cfsba = get_child_stat(fsb, fsa)
assert fsb.ttot == 10
assert fsb.tsub == 1
assert fsa.ttot == 13
assert fsa.tsub == 12
assert cfsaa.ttot == 5
assert cfsaa.tsub == 5
assert cfsba.ttot == 9
assert cfsba.tsub == 4
#stats.debug_print()
test_end("recursive function (abaa)")

test_start()
_timings = {"a_1":13,"a_2":10,"b_1":9,"b_2":5}
_yappi.set_test_timings(_timings)

ncall = 1
def a():
    global ncall
    if ncall == 1:
        ncall += 1
        a()
    elif ncall == 2:        
        b()
    else:
        return
def b():
    global ncall
    if ncall == 2:
        ncall += 1
        b()
    else:
        return
    
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
cfsaa = get_child_stat(fsa, fsa)
cfsab = get_child_stat(fsa, fsb)
cfsbb = get_child_stat(fsb, fsb)
assert fsa.ttot == 13
assert fsa.tsub == 4
assert fsb.ttot == 9
assert fsb.tsub == 9
assert cfsaa.ttot == 10
assert cfsaa.tsub == 1
assert cfsab.ttot == 9
assert cfsab.tsub == 4
assert cfsbb.ttot == 5
assert cfsbb.tsub == 5
#stats.debug_print()
test_end("recursive function (aabb)")

test_start()
_timings = {"a_1":13,"b_1":10,"b_2":6,"b_3":1}
_yappi.set_test_timings(_timings)

ncall = 1
def a():
    global ncall
    if ncall == 1:
        b()
def b():
    global ncall
    if ncall == 3:
        return
    ncall += 1
    b()
    
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
cfsab = get_child_stat(fsa, fsb)
cfsbb = get_child_stat(fsb, fsb)
assert fsa.ttot == 13
assert fsa.tsub == 3
assert fsb.ttot == 10
assert fsb.tsub == 10
assert fsb.ncall == 3
assert fsb.nactualcall == 1
assert cfsab.ttot == 10
assert cfsab.tsub == 4
assert cfsbb.ttot == 6
assert cfsbb.tsub == 6
assert cfsbb.nactualcall == 0
assert cfsbb.ncall == 2
#stats.debug_print()
test_end("recursive function (abbb)")

test_start()
_timings = {"a_1":13,"a_2":10,"a_3":6,"b_1":1}
_yappi.set_test_timings(_timings)

ncall = 1
def a():
    global ncall
    if ncall == 3:
        b()
        return
    ncall += 1
    a()
def b():
    return
    
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
cfsaa = get_child_stat(fsa, fsa)
cfsab = get_child_stat(fsa, fsb)
assert fsa.ttot == 13
assert fsa.tsub == 12
assert fsb.ttot == 1
assert fsb.tsub == 1
assert cfsaa.ttot == 10
assert cfsaa.tsub == 9
assert cfsab.ttot == 1
assert cfsab.tsub == 1
#stats.debug_print()
test_end("recursive function (aaab)")

test_start()
_timings = {"a_1":13,"b_1":10,"a_2":6,"b_2":1}
_yappi.set_test_timings(_timings)

ncall = 1
def a():
    b()
def b():
    global ncall
    if ncall == 2:
        return
    ncall += 1
    a()
    
yappi.start()
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('a')
fsb = stats.find_by_name('b')
cfsab = get_child_stat(fsa, fsb)
cfsba = get_child_stat(fsb, fsa)
assert fsa.ttot == 13
assert fsa.tsub == 8
assert fsb.ttot == 10
assert fsb.tsub == 5
assert cfsab.ttot == 10
assert cfsab.tsub == 5
assert cfsab.ncall == 2
assert cfsab.nactualcall == 1
assert cfsba.ttot == 6
assert cfsba.tsub == 5
#stats.debug_print()
test_end("recursive function (abab)")

test_start()
def a():
    time.sleep(0.4) # is a builtin function
yappi.set_clock_type('wall')

yappi.start(builtins=True)
a()
stats = yappi.get_func_stats()
fsa = stats.find_by_name('sleep')
assert fsa is not None
assert fsa.ttot > 0.3
test_end('start parameters (builtin+clock_type)')

test_start()
yappi.set_clock_type('wall')
def a():
    time.sleep(0.2)
class Worker1(threading.Thread):
    def a(self):
        time.sleep(0.3)
    def run(self):
        self.a()
yappi.start(builtins=False, profile_threads=True)

c = Worker1()
c.start()
c.join()
a()
stats = yappi.get_func_stats()
fsa1 = stats.find_by_name('Worker1.a')
fsa2 = stats.find_by_name('a')
assert fsa1 is not None
assert fsa2 is not None
assert fsa1.ttot > 0.2
assert fsa2.ttot > 0.1
test_end('start parameters (multithread=True)')

test_start()
yappi.set_clock_type('wall')
def a():
    time.sleep(0.2)
class Worker1(threading.Thread):
    def a(self):
        time.sleep(0.3)
    def run(self):
        self.a()
yappi.start(profile_threads=False)

c = Worker1()
c.start()
c.join()
a()

stats = yappi.get_func_stats()
fsa1 = stats.find_by_name('Worker1.a')
fsa2 = stats.find_by_name('a')
assert fsa1 is None
assert fsa2 is not None
assert fsa2.ttot > 0.1

#fsa2 = stats.find_by_name('a')
#stats.print_all()
test_end('start parameters (multithread=False)')


test_start()
_timings = {"a_1":6,"b_1":4}
_yappi.set_test_timings(_timings)

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
test_end("stop in the middle")

test_end("FUNCTIONALITY TESTS")

