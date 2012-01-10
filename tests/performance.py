
import yappi
import time

def foo():
    pass
    
def bar():
    for i in range(5000000):
        foo()

yappi.start()
t0 = time.time()
bar()
print "Elapsed1 %f secs." % (time.time()-t0)
yappi.print_stats()

t0 = time.time()
import cProfile
cProfile.run('bar()')
print "Elapsed1 %f secs." % (time.time()-t0)