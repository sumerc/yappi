import threading

class FancyThread(threading.Thread):
    def run(self):
        pass

t = FancyThread()
t.start()
t.join()
