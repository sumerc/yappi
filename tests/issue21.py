import yappi
import time
import threading
import sys

class MyThread(threading.Thread):
    def run(self):
        time.sleep(1)

n =     25

yappi.start()
for i in range(0,n):
    c = MyThread()
    c.start()
time.sleep(1)
yappi.print_stats()
yappi.stop()