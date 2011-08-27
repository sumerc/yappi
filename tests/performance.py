
import yappi
import time

def foo():
    pass

yappi.start()

t0 = time.time()
for i in range(5000000):
    foo()
print "Elapsed %f secs." % (time.time()-t0)
#yappi.print_stats()
