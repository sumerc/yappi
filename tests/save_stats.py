import time
import yappi
import _yappi

timings = {"a_1":4, "b_1":1}
_yappi._set_test_timings(timings)

def profile(func):
    def wrapped(*args, **kwargs):
        yappi.start()
        result = func(*args, **kwargs)
        yappi.stop()
        prof_file = "%s.%s" % (func.__name__, time.time())
        #prof_file = "callgrind.a.1"
        yappi.get_func_stats().save(prof_file, "ystat")
        return result
    return wrapped

def b():
    pass

@profile
def a():
    b()

a()
