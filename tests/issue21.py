import yappi
import time
import threading
import sys

class MyThread(threading.Thread):
    def run(self):
        time.sleep(1)

def foo():
    n = 25
    for i in range(0,n):
        c = MyThread()
        c.start()


yappi.start()
foo()
yappi.print_stats()

import cProfile
cProfile.run('foo()')
