import sys
import yappi
import unittest

class YappiUnitTestCase(unittest.TestCase):
    def setUp(self):
        if yappi.is_running():
            yappi.stop()
        yappi.clear_stats()
        yappi.set_clock_type('cpu') # reset to default clock type

    def tearDown(self):
        pass
        
def assert_raises_exception(func):
    try:
        _run(func)
        assert 0 == 1
    except:
        pass
        
def run_with_yappi(func, *args, **kwargs):
    yappi.start()
    func(*args, **kwargs)
    yappi.stop()

def run_and_get_func_stats(func, ):
    func(*args, **kwargs)
    return yappi.get_func_stats(**kwargs)

def run_and_get_thread_stats(func, **kwargs):
    _run_with_yappi(func)
    return yappi.get_thread_stats(**kwargs)

# both parent and child are YFuncStat objects
def get_child_stat(parent, child):
    for item in parent.children:
        if item.index == child.index:
            return item