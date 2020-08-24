import unittest
import yappi
import gevent
from gevent.event import Event
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
        ../yappi/tests/utils.py:126 burn_cpu  2      0.000000  0.600026  0.300013
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


    def test_recursive_function(self):
        def a(n):
            gevent.sleep(0.001)
            burn_cpu(0.1)
            if (n <= 0):
                return

            a(n - 1)
            a(n - 2)

        def driver():
            gls = []
            for i in (3, 4):
                gls.append(gevent.spawn(a, i))
            for gl in gls:
                gl.get()

        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")
        yappi.start()
        driver()
        yappi.stop()

        r1 = '''
        tests/test_gevent.py:84 a             24/2   0.000524  2.402342  0.100098
        ../yappi/tests/utils.py:126 burn_cpu  24     0.000000  2.400939  0.100039
        ..e-packages/gevent/hub.py:126 sleep  24     0.000879  0.000879  0.000037
        tests/test_gevent.py:93 driver        1      0.000202  0.000820  0.000820
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

    def test_exception_raised(self):
        def a(n):
            burn_cpu(0.1)
            gevent.sleep(0.1)

            if (n == 0):
                raise Exception

            a(n-1)

        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")
        yappi.start()

        try:
            gevent.spawn(a, 3).get()
        except Exception:
            pass

        yappi.stop()
        stats = yappi.get_func_stats()
        t1 = '''
        tests/test_gevent.py:118 a            4/1    0.000149  0.400614  0.100153
        ../yappi/tests/utils.py:126 burn_cpu  4      0.000000  0.400208  0.100052
        '''
        self.assert_traces_almost_equal(t1, stats)

    def test_greenlets_spawned_before_profile(self):

        def a(ev1, ev2):
            a_inner_1(ev1, ev2)
            burn_cpu(0.1)

        def a_inner_1(ev1, ev2):
            a_inner_2(ev1, ev2)
            burn_cpu(0.1)

        def a_inner_2(ev1, ev2):
            ev1.set()
            ev2.wait()

            a_inner_3()

        def a_inner_3():
            burn_cpu(0.1)
            gevent.sleep(0.1)


        ev1 = Event()
        ev2 = Event()
        gl = gevent.spawn(a, ev1, ev2)

        # wait for greenlet to pause
        ev1.wait()

        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")
        yappi.start()

        # resume greenlet and wait for completion
        ev2.set()
        gl.get()

        yappi.stop()
        stats = yappi.get_func_stats()
        t1 = '''
        ../yappi/tests/utils.py:126 burn_cpu  3      0.000000  0.300119  0.100040
        tests/test_gevent.py:161 a_inner_3    1      0.000041  0.100209  0.100209
        '''
        self.assert_traces_almost_equal(t1, stats)

    def test_many_context_switches(self):

        def common():
            for _ in range(100):
                gevent.sleep(0.001)

            burn_io(0.1)
            burn_cpu(0.2)

            for _ in range(100):
                gevent.sleep(0.001)

            burn_io(0.1)
            burn_cpu(0.2)

        def a():
            common()

        def b():
            common()

        def driver():
            gls = []
            for func in (a, a, b, b):
                gls.append(gevent.spawn(func))

            for gl in gls:
                gl.get()

        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")
        yappi.start()
        driver()
        yappi.stop()

        stats = yappi.get_func_stats()
        t1 = '''
        tests/test_gevent.py:128 common       4      0.004040  1.619333  0.404833
        ../yappi/tests/utils.py:126 burn_cpu  8      0.000000  1.600398  0.200050
        tests/test_gevent.py:141 a            2      0.000021  0.810061  0.405030
        tests/test_gevent.py:144 b            2      0.000021  0.809314  0.404657
        '''
        self.assert_traces_almost_equal(t1, stats)

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
        ../yappi/tests/utils.py:126 burn_cpu  12     0.000000  3.801261  0.316772
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
        ../yappi/tests/utils.py:126 burn_cpu  5      0.000000  1.500896  0.300179
        '''
        self.assert_traces_almost_equal(t1, traces)

    def test_profile_threads_false(self):

        def recursive_a(n):
            if not n:
                return
            burn_cpu(0.1)
            gevent.sleep(0.1)
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
        tests/test_gevent.py:359 driver       1      0.000061  0.101845  0.101845
        tests/test_gevent.py:335 recursive_a  1      0.000262  0.100619  0.100619
        ../yappi/tests/utils.py:126 burn_cpu  1      0.000000  0.100082  0.100082
        '''
        self.assert_traces_almost_equal(t1, traces)


if __name__ == '__main__':
    unittest.main()
