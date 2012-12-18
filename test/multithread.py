
import time 
import threading
import yappi

class WorkerThread(threading.Thread):
    def foo(self):
        for i in range(1000000): pass
    def run(self):
        for i in range(1000000): pass
        self.foo()
        
class WorkerThread2(threading.Thread):
    def run(self):
        import time 
        time.sleep(2.0)
        for i in range(1000000): pass
        
class IOThread(threading.Thread):
    def run(self):        
        time.sleep(2.0)
        for i in range(1000000): pass
        
yappi.start()

l = []
c = WorkerThread()
c.start()

c = WorkerThread2()
c.start()

c = IOThread()
c.start()

time.sleep(1.0)

yappi.print_func_stats(sort_type=yappi.SORTTYPE_TTOT)
yappi.print_thread_stats()

"""
f = open("den.txt", "w")
yappi.print_stats(f)
yappi.stop()
"""
