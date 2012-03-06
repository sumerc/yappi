import time
import yappi
import threading
from test_utils import func_stat_from_name, assert_raises_exception, run_with_yappi, test_passed

"""
NOTE: Please note that below tests are only for development, on some _slow_ hardware they may fail.
There are implicit assumptions on how much time a specific statement can take at much. Tested on
i5 2.8 and AMD Dual 2.4 processors.
"""

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
    
stats = run_with_yappi('foo()')
fs = func_stat_from_name(stats, 'foo')
assert fs != None
assert fs.ttot < 1.0
assert fs.tsub < 1.0
assert fs.ncall == 1

test_passed("trivial timing function")
    
# try get_stats after clear_stats
yappi.clear_stats()
assert_raises_exception('yappi.get_stats()')

# try profiling a simple recursive function
def fib(n):
   if n > 1:
       return fib(n-1) + fib(n-2)
   else:
       return n

stats = run_with_yappi('fib(22)')
fs = func_stat_from_name(stats, 'fib')
assert fs.ncall == 57313
assert fs.ttot == fs.tsub
yappi.clear_stats()

test_passed("recursive function")

# try profiling a chained-recursive function
ncount = 3
ncc = 0
def a():
    for i in range(1000000): pass
    global ncount
    global ncc
    if ncc == ncount:
        return
    ncc += 1
    b()
    
def b():
    for i in range(1000000): pass
    a()
    time.sleep(1.0)
    
stats = run_with_yappi('a()')  
fsa = func_stat_from_name(stats, '.a:')
fsb = func_stat_from_name(stats, '.b:')
assert fsa.ncall == 4
assert fsa.tsub < fsa.ttot
assert fsa.ttot >= fsb.ttot
assert fsb.ncall == 3
assert fsa.ttot <= 3.0
assert fsb.ttot <= 3.0
yappi.clear_stats()

def x(n):
    if n==0:
        return
    y(n)
    
def y(n):
    time.sleep(1.0)
    z(n)
    
def z(n):
    x(n-1)
stats = run_with_yappi('x(2)')  
fsx = func_stat_from_name(stats, '.x:')
fsy = func_stat_from_name(stats, '.y:')
fsz = func_stat_from_name(stats, '.z:')

yappi.clear_stats()
test_passed("chained-recursive function #2")
"""
class MyThread(threading.Thread):
    
    def __init__(self, tid):
        self._tid = tid
        threading.Thread.__init__(self)
    
    def sleep1(self):
        pass
    
    def run(self):
        for i in range(1000000): pass
        time.sleep(1.0)
        
def bar():
    n = 25
    for i in range(0,n):
        c = MyThread(i)
        c.start()
        #c.join()
    time.sleep(1.0)
stats = run_with_yappi('bar()')
fsa = func_stat_from_name(stats, '.run:')
print(fsa.ttot)
import yappi
yappi.print_stats()
test_passed("trivial multithread function")
"""
test_passed("General tests passed.:)")