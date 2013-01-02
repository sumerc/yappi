
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
        
#yappi.start(profile_threads=False)
yappi.start()

l = []
c = WorkerThread()
c.start()

c = WorkerThread2()
c.start()

c = IOThread()
c.start()

time.sleep(1.0)

yappi.get_func_stats().print_all()
yappi.get_thread_stats().print_all()

