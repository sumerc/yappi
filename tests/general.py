import time
import yappi
from test_utils import func_stat_from_name, assert_raises_exception, run_with_yappi

# try get_stats() before start
assert_raises_exception('yappi.get_stats()')

# try clear_stats() while running
assert_raises_exception('yappi.clear_stats()')

# trivial function timing check
def foo():
    import time
    time.sleep(1.2)
    
stats = run_with_yappi('foo()')
fs = func_stat_from_name(stats, 'foo')
assert fs != None
assert fs.ttot > 1.0
assert fs.tsub < 1.0
assert fs.ncall == 1   
    
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

# try profiling a chained-recursive function
ncount = 5
ncc = 0
def a():
    global ncount
    global ncc
    if ncc == ncount:
        return
    ncc += 1
    b()
    
def b():
    time.sleep(1.1)
    a()
    
stats = run_with_yappi('a()')  
fsa = func_stat_from_name(stats, 'general.py.a:')
fsb = func_stat_from_name(stats, 'general.py.b:')
assert fsa.ncall == 6
assert fsa.tsub < fsa.ttot
assert fsa.ttot >= fsb.ttot
assert fsb.ncall == 5
assert fsa.ttot >= 5.0
assert fsb.ttot >= 5.0
#assert fs.ttot == fs.tsub
#yappi.clear_stats()
yappi.print_stats()

#import cProfile -- cProfile does have a bug with chained recursive funcs?
#cProfile.run('a()')   

print "\r\nGeneral tests passed...\r\n"