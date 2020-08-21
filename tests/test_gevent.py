import unittest
import yappi
import gevent
import greenlet
import gevent.monkey
import threading
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io

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
        yappi.set_context_backend("greenlet")
        yappi.start()
        g = gevent.spawn(a, 3)
        g.get() # run until complete, report exception (if any)
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:11 a  9      0.000124  0.400667  0.044519
        ../yappi/tests/utils.py:126 burn_cpu  4      0.000000  0.400099  0.100025
        sleep                                 4      0.000000  0.000444  0.000111
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
        yappi.set_context_backend("greenlet")
        yappi.start(builtins=True)
        g1 = gevent.spawn(a)
        g1.get()
        g2 = gevent.spawn(a)
        g2.get()
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.000118  1.604049  0.802024
        ..e-packages/gevent/hub.py:126 sleep  6      0.000000  0.603239  0.100540
        ../yappi/tests/utils.py:126 burn_cpu  2      0.446499  0.600026  0.300013
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
        ..e-packages/gevent/hub.py:126 sleep  6      0.000159  0.000801  0.000134
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
            burn_cpu(0.3)
            gevent.sleep(0.3)
            g = gevent.spawn(recursive_a, n - 1)
            return g.get()

        tlocal = threading.local()

        def tag_cbk():
            try:
                return tlocal._tag
            except:
                return -1

        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")
        tlocal._tag = 0
        yappi.set_tag_callback(tag_cbk)

        class GeventTestThread(threading.Thread):
            def __init__(self, tag, func, args):
                super(GeventTestThread, self).__init__()
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

        def driver():
            _ctag = 1

            to_run = [
                (a, ()),
                (b, ()),
                (recursive_a, (5,)),
                (recursive_a, (5,))
            ]

            ts = []
            for func, args in to_run:
                t = GeventTestThread(_ctag, func, args)
                t.start()

                ts.append(t)
                _ctag += 1

            for t in ts:
                t.result()

        yappi.start()

        driver()

        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        ../yappi/tests/utils.py:126 burn_cpu  12     2.529676  3.801261  0.316772
        tests/test_gevent.py:96 recursive_a   12     0.001707  3.014276  0.251190
        tests/test_gevent.py:88 a             2      0.000088  0.800840  0.400420
        ..e-packages/gevent/hub.py:126 sleep  12     0.011484  0.011484  0.000957
        tests/test_gevent.py:132 driver       1      0.000169  0.009707  0.009707
        tests/test_gevent.py:92 b             1      0.000121  0.000162  0.000162
        '''
        self.assert_traces_almost_equal(t1, traces)

        traces = yappi.get_func_stats(filter={'tag': 3})
        t1 = '''
        tests/test_gevent.py:101 recursive_a  6      0.001180  1.503081  0.250514
        ../yappi/tests/utils.py:126 burn_cpu  5      1.117260  1.500896  0.300179
        '''
        self.assert_traces_almost_equal(t1, traces)

    def test_profile_threads_false(self):

        def recursive_a(n):
            if not n:
                return
            burn_cpu(0.3)
            gevent.sleep(0.3)
            g = gevent.spawn(recursive_a, n - 1)
            return g.get()


        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")

        class GeventTestThread(threading.Thread):
            def __init__(self, func, args):
                super(GeventTestThread, self).__init__()
                self.func = func
                self.args = args
            def run(self):
                self.g = gevent.spawn(self.func, *self.args)
                self.g.join()
            def result(self):
                self.join() # wait for thread completion
                return self.g.get() # get greenlet result

        def driver():

            to_run = [
                (recursive_a, (5,)),
                (recursive_a, (5,))
            ]

            ts = []
            for func, args in to_run:
                t = GeventTestThread(func, args)
                t.start()
                ts.append(t)

            recursive_a(6)

            for t in ts:
                t.result()

        yappi.start(profile_threads=False)

        driver()

        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        tests/test_gevent.py:212 driver       1      0.000107  0.302162  0.302162
        tests/test_gevent.py:178 recursive_a  1      0.000195  0.300475  0.300475
        ../yappi/tests/utils.py:126 burn_cpu  1      0.208068  0.300043  0.300043
        '''
        self.assert_traces_almost_equal(t1, traces)

if __name__ == '__main__':
    unittest.main()
