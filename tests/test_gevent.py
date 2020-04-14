import unittest
import yappi
import gevent
import gevent.monkey
import threading
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io

# the next line enables gevent monkey-patching
gevent.monkey.patch_all(thread=False) # patch everything, except threads
# 'burn_io' will still simulate I/O (will do a gevent sleep instead of
# time.sleep, in fact)

class SingleThreadTests(YappiUnitTestCase):

    def test_recursive_coroutine(self):

        def a(n):
            if n <= 0:
                return
            gevent.sleep(0.1)
            burn_cpu(0.1)
            g1 = gevent.spawn(a, n - 1)
            g1.get()
            g2 = gevent.spawn(a, n - 2)
            g2.get()

        yappi.set_clock_type("cpu")
        yappi.start()
        g = gevent.spawn(a, 3)
        g.get() # run until complete, report exception (if any)
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:11 a  9/1    0.000124  0.400667  0.044519
        ../yappi/tests/utils.py:126 burn_cpu  4      0.000000  0.400099  0.100025
        async_sleep                           4      0.000000  0.000444  0.000111
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

    def test_basic_old_style(self):

        def a():
            gevent.sleep(0.1)
            burn_io(0.1)
            gevent.sleep(0.1)
            burn_io(0.1)
            gevent.sleep(0.1)
            burn_cpu(0.3)

        yappi.set_clock_type("wall")
        yappi.start(builtins=True)
        g1 = gevent.spawn(a)
        g1.get()
        g2 = gevent.spawn(a)
        g2.get()
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.000118  1.604049  0.802024
        async_sleep                           6      0.000000  0.603239  0.100540
        ../yappi/tests/utils.py:126 burn_cpu  2      0.576313  0.600026  0.300013
        ..p/yappi/tests/utils.py:135 burn_io  4      0.000025  0.400666  0.100166
        time.sleep                            4      0.400641  0.400641  0.100160
        '''
        stats = yappi.get_func_stats()

        self.assert_traces_almost_equal(r1, stats)

        yappi.clear_stats()
        yappi.set_clock_type("cpu")
        yappi.start(builtins=True)
        g1 = gevent.spawn(a)
        g1.get()
        g2 = gevent.spawn(a)
        g2.get()
        yappi.stop()
        stats = yappi.get_func_stats()
        r1 = '''
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.000117  0.601170  0.300585
        ../yappi/tests/utils.py:126 burn_cpu  2      0.000000  0.600047  0.300024
        async_sleep                           6      0.000159  0.000801  0.000134
        time.sleep                            4      0.000169  0.000169  0.000042
        '''
        self.assert_traces_almost_equal(r1, stats)


class MultiThreadTests(YappiUnitTestCase):

    def test_basic(self):

        def a():
            gevent.sleep(0.3)
            burn_cpu(0.4)

        def b():
            g = gevent.spawn(a)
            return g.get()

        def recursive_a(n):
            if not n:
                return
            burn_io(0.3)
            gevent.sleep(0.3)
            g = gevent.spawn(recursive_a, n - 1)
            return g.get()

        tlocal = threading.local()

        def tag_cbk():
            try:
                return tlocal._tag
            except:
                return -1

        yappi.set_clock_type("wall")
        tlocal._tag = 0
        yappi.set_tag_callback(tag_cbk)

        class GeventTestThread(threading.Thread):
            def __init__(self, tag, func, args):
                super().__init__()
                self.tag = tag
                self.func = func
                self.args = args
            def run(self):
                tlocal._tag = self.tag
                self.g = gevent.spawn(self.func, *self.args)
                self.g.join()
            def result(self):
                self.join() # wait for thread completion
                return self.g.get() # get greenlet result

        _ctag = 1

        ts = []
        for func, args in ((a, ()), (recursive_a, (5,)), (b, ())):
            t = GeventTestThread(_ctag, func, args)
            t.start()

            ts.append(t)
            _ctag += 1

        def driver():
            for t in ts:
                t.result()

        yappi.start()

        driver()

        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        tests/test_asyncio.py:137 driver      1      0.000061  3.744064  3.744064
        tests/test_asyncio.py:96 recursive_a  6/1    0.000188  3.739663  0.623277
        tests/test_asyncio.py:8 async_sleep   7      0.000085  2.375271  0.339324
        tests/utils.py:135 burn_io            5      0.000044  1.700000  0.437400
        tests/test_asyncio.py:87 a            2      0.000019  1.600000  0.921138
        tests/utils.py:126 burn_cpu           2      0.800000  0.800000  0.509730
        tests/test_asyncio.py:92 b            1      0.000005  0.800000  0.921055
        '''
        self.assert_traces_almost_equal(t1, traces)

        traces = yappi.get_func_stats(filter={'tag': 2})
        t1 = '''
        tests/test_asyncio.py:96 recursive_a  6/1    0.000211  3.720011  0.620002
        tests/utils.py:135 burn_io            5      0.000079  1.700000  0.431813
        async_sleep                           5      0.000170  1.560735  0.312147
        '''
        self.assert_traces_almost_equal(t1, traces)


if __name__ == '__main__':
    unittest.main()
