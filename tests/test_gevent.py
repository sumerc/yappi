import unittest
import _yappi
import yappi
import gevent
from gevent.event import Event
import threading
from utils import (
    YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io,
    burn_io_gevent
)

class GeventTestThread(threading.Thread):
    def __init__(self, name, *args, **kwargs):
        super(GeventTestThread, self).__init__(*args, **kwargs)
        self.name = name

    def run(self):
        gevent.getcurrent().name = self.name
        gevent.get_hub().name = "Hub"
        super(GeventTestThread, self).run()

class GeventTest(YappiUnitTestCase):

    def setUp(self):
        super(GeventTest, self).setUp()
        yappi.set_clock_type("cpu")
        yappi.set_context_backend("greenlet")
        yappi.set_context_name_callback(self.get_greenlet_name)
        gevent.getcurrent().name = "Main"
        gevent.get_hub().name = "Hub"

    @classmethod
    def get_greenlet_name(cls):
        try:
            return gevent.getcurrent().name
        except AttributeError:
            return None

    @classmethod
    def spawn_greenlet(cls, name, func, *args, **kwargs):
        name = "%s/%s" % (cls.get_greenlet_name(), name)
        gl = gevent.Greenlet(func, *args, **kwargs)
        gl.name = name
        gl.start()
        return gl

    @classmethod
    def spawn_thread(cls, name, func, *args, **kwargs):
        name = "%s/%s" % (cls.get_greenlet_name(), name)
        t = GeventTestThread(name, target=func, args=args, kwargs=kwargs)
        t.start()
        return t

class TestAPI(GeventTest):

    def test_start_flags(self):
        self.assertEqual(_yappi._get_start_flags(), None)
        yappi.start()

        def a():
            pass

        a()
        self.assertEqual(_yappi._get_start_flags()["profile_builtins"], 0)
        self.assertEqual(_yappi._get_start_flags()["profile_multicontext"], 1)
        self.assertEqual(len(yappi.get_greenlet_stats()), 1)

        yappi.stop()
        yappi.clear_stats()

        yappi.start(builtins=True, profile_greenlets=True, profile_threads=False)
        self.assertEqual(_yappi._get_start_flags()["profile_builtins"], 1)
        self.assertEqual(_yappi._get_start_flags()["profile_multicontext"], 1)
        self.assertEqual(len(yappi.get_greenlet_stats()), 1)
        yappi.stop()

    def test_context_change_exception(self):
        yappi.start()
        def a():
            pass

        a()
        # Setting to same backend should succeed
        # Changing backend should fail
        self.assertRaises(_yappi.error, yappi.set_context_backend, "native_thread")
        yappi.stop()
        # Still fail, stats need to be cleared
        self.assertRaises(_yappi.error, yappi.set_context_backend, "native_thread")
        yappi.clear_stats()
        # Should succeed now
        yappi.set_context_backend("native_thread")
        yappi.stop()

    def test_get_context_stat_exception(self):
        yappi.start()
        def a():
            pass

        a()
        yappi.stop()
        self.assertRaises(yappi.YappiError, yappi.get_thread_stats)
        self.assertEqual(len(yappi.get_greenlet_stats()), 1)

    def test_context_cbks_reset_to_default(self):
        yappi.set_context_backend("greenlet")
        yappi.set_context_backend("native_thread")

        class ThreadA(threading.Thread):
            def run(self):
                burn_cpu(0.05)

        def a():
            pass

        yappi.start()

        t = ThreadA()
        t.start()
        t.join()

        # Spawn a greenlet to test that greenlet context is not recognised
        g = gevent.Greenlet(a)
        g.start()
        g.get()

        yappi.stop()

        tstats = yappi.get_thread_stats()

        self.assertEqual(len(tstats), 2, "Incorrect number of contexts captured")

        # First stat should be of threadA since it is sorted by ttot
        statsA = tstats[0]
        self.assertEqual(statsA.tid, t.ident)
        self.assertEqual(statsA.name, t.__class__.__name__)

        statsMain = tstats[1]
        main_thread = threading.current_thread()
        self.assertEqual(statsMain.tid, main_thread.ident)
        self.assertEqual(statsMain.name, main_thread.__class__.__name__)

class SingleThreadTests(GeventTest):

    def test_recursive_greenlet(self):

        def a(n):
            if n <= 0:
                return
            burn_io_gevent(0.1)
            burn_cpu(0.1)
            g1 = self.spawn_greenlet("a_%d" % (n-1), a, n - 1)
            g1.get()
            g2 = self.spawn_greenlet("a_%d" % (n-2), a, n - 2)
            g2.get()

        yappi.start()
        g = self.spawn_greenlet("a", a, 3)
        g.get() # run until complete, report exception (if any)
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:11 a  9      0.000124  0.400667  0.044519
        ../yappi/tests/utils.py:126 burn_cpu  4      0.000000  0.400099  0.100025
        sleep                                 4      0.000000  0.000444  0.000111
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main/a/a_1            9      0.100588  3
        Main/a/a_2            4      0.100588  3
        Main/a                3      0.100584  3
        Main/a/a_2/a_1        5      0.100549  3
        Main                  1      0.000356  2
        Main/a/a_1/a_0        10     0.000046  1
        Main/a/a_2/a_1/a_0    6      0.000044  1
        Main/a/a_2/a_1/a_-1   7      0.000036  1
        Main/a/a_2/a_0        8      0.000035  1
        Main/a/a_1/a_-1       11     0.000029  1
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

    def test_basic_old_style(self):

        def a():
            burn_io_gevent(0.1)
            burn_io(0.1)
            burn_io_gevent(0.1)
            burn_io(0.1)
            burn_io_gevent(0.1)
            burn_cpu(0.3)

        yappi.set_clock_type("wall")
        yappi.start(builtins=True)
        g1 = self.spawn_greenlet("a_1", a)
        g1.get()
        g2 = self.spawn_greenlet("a_2", a)
        g2.get()
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.000118  1.604049  0.802024
        burn_io_gevent                        6      0.000000  0.603239  0.100540
        ../yappi/tests/utils.py:126 burn_cpu  2      0.000000  0.600026  0.300013
        ..p/yappi/tests/utils.py:135 burn_io  4      0.000025  0.400666  0.100166
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)
        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main           1      1.623057  3
        Main/a_1       3      0.812399  1
        Main/a_2       4      0.810234  1
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

        yappi.clear_stats()
        yappi.set_clock_type("cpu")
        yappi.start(builtins=True)
        g1 = self.spawn_greenlet("a_1", a)
        g1.get()
        g2 = self.spawn_greenlet("a_2", a)
        g2.get()
        yappi.stop()
        stats = yappi.get_func_stats()
        r1 = '''
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.000117  0.601170  0.300585
        ../yappi/tests/utils.py:126 burn_cpu  2      0.000000  0.600047  0.300024
        burn_io_gevent                        6      0.000159  0.000801  0.000134
        '''
        self.assert_traces_almost_equal(r1, stats)
        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main/a_2       6      0.301190  1
        Main/a_1       5      0.300960  1
        Main           1      0.000447  3
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

    def test_recursive_function(self):
        def a(n):
            if (n <= 0):
                return

            burn_io_gevent(0.001)
            burn_cpu(0.1)

            a(n - 1)
            a(n - 2)

        def driver():
            gls = []
            for i in (3, 4):
                gls.append(self.spawn_greenlet("recursive_%d" % (i), a, i))
            for gl in gls:
                gl.get()

        yappi.set_clock_type("cpu")
        yappi.start()
        driver()
        yappi.stop()

        r1 = '''
        tests/test_gevent.py:209 a            24/2   0.000407  1.102129  0.045922
        ../yappi/tests/utils.py:142 burn_cpu  11     0.000000  1.100660  0.100060
        ../tests/utils.py:154 burn_io_gevent  11     0.000159  0.001062  0.000097
        ..e-packages/gevent/hub.py:126 sleep  11     0.000903  0.000903  0.000082
        tests/test_gevent.py:219 driver       1      0.000208  0.000467  0.000467
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main/recursive_4  4      0.701283  5
        Main/recursive_3  3      0.400664  5
        Main              1      0.000439  3
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

    def test_exception_raised(self):
        def a(n):
            burn_cpu(0.1)
            burn_io_gevent(0.1)

            if (n == 0):
                raise Exception

            a(n-1)

        yappi.set_clock_type("cpu")
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
            burn_io_gevent(0.1)


        ev1 = Event()
        ev2 = Event()
        gl = self.spawn_greenlet("a", a, ev1, ev2)

        # wait for greenlet to pause
        ev1.wait()

        yappi.set_clock_type("cpu")
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
        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main/a                2      0.300425  1
        Main                  1      0.000145  2
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)


    def test_many_context_switches(self):

        def common():
            for _ in range(100):
                burn_io_gevent(0.001)

            burn_io(0.1)
            burn_cpu(0.2)

            for _ in range(100):
                burn_io_gevent(0.001)

            burn_io(0.1)
            burn_cpu(0.2)

        def a():
            common()

        def b():
            common()

        def driver():
            gls = []
            for idx, func in enumerate((a, a, b, b)):
                gls.append(self.spawn_greenlet("func_%d" % (idx), func))

            for gl in gls:
                gl.get()

        yappi.set_clock_type("cpu")
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
        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main/func_3    6      0.417321  201
        Main/func_2    5      0.416521  201
        Main/func_0    3      0.414553  201
        Main/func_1    4      0.413268  201
        Main           1      0.000579  3
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

    def test_default_context_name_cbk(self):

        # Set context backend to configure default callbacks
        yappi.set_context_backend("greenlet")

        def a():
            burn_cpu(0.1)

        class GreenletA(gevent.Greenlet):
            pass

        yappi.start()
        g = GreenletA(a)
        g.start()
        g.get()
        yappi.stop()

        gstats = yappi.get_greenlet_stats()
        r2 = '''
        GreenletA      3      0.100060  1
        greenlet       1      0.000240  2
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)


class MultiThreadTests(GeventTest):

    def test_basic(self):

        def a():
            burn_io_gevent(0.3)
            burn_cpu(0.4)

        def b():
            g = self.spawn_greenlet("a", a)
            return g.get()

        def recursive_a(n):
            if not n:
                return
            burn_cpu(0.3)
            burn_io_gevent(0.3)
            g = self.spawn_greenlet("rec_a", recursive_a, n - 1)
            return g.get()

        yappi.set_clock_type("cpu")

        def driver():
            to_run = [
                (a, ()),
                (b, ()),
                (recursive_a, (5,)),
                (recursive_a, (5,))
            ]

            ts = []
            for idx, (func, args) in enumerate(to_run):
                t = self.spawn_thread("%s-%d" %  (func.__name__, idx), func, *args)
                ts.append(t)

            for t in ts:
                t.join()

        yappi.start()

        driver()

        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        ../yappi/tests/utils.py:126 burn_cpu  12     0.000000  3.801261  0.316772
        tests/test_gevent.py:96 recursive_a   12     0.001707  3.014276  0.251190
        tests/test_gevent.py:88 a             2      0.000088  0.800840  0.400420
        burn_io_gevent                        12     0.011484  0.011484  0.000957
        tests/test_gevent.py:132 driver       1      0.000169  0.009707  0.009707
        tests/test_gevent.py:92 b             1      0.000121  0.000162  0.000162
        '''
        self.assert_traces_almost_equal(t1, traces)

        stats = yappi.get_greenlet_stats()
        r2 = '''
        Main/a-0                                            2      0.400421  59
        Main/b-1/a                                          6      0.400228  58
        Main/recursive_a-3                                  8      0.301177  33
        Main/recursive_a-2                                  7      0.300615  36
        Main/recursive_a-2/rec_a/rec_a/rec_a                16     0.300509  42
        Main/recursive_a-2/rec_a/rec_a/rec_a/rec_a          18     0.300505  42
        Main/recursive_a-3/rec_a/rec_a/rec_a/rec_a          17     0.300481  39
        Main/recursive_a-3/rec_a                            11     0.300464  45
        Main/recursive_a-3/rec_a/rec_a                      13     0.300456  35
        Main/recursive_a-3/rec_a/rec_a/rec_a                15     0.300456  36
        Main/recursive_a-2/rec_a/rec_a                      14     0.300423  29
        Main/recursive_a-2/rec_a                            12     0.300359  41
        Main                                                1      0.002443  7
        Main/b-1                                            4      0.000595  2
        Main/recursive_a-3/rec_a/rec_a/rec_a/rec_a/rec_a    19     0.000048  1
        Main/recursive_a-2/rec_a/rec_a/rec_a/rec_a/rec_a    20     0.000047  1
        '''
        self.assert_ctx_stats_almost_equal(r2, stats)

    def test_profile_greenlets_false(self):

        def recursive_a(n):
            if not n:
                return
            burn_cpu(0.1)
            burn_io_gevent(0.1)
            g = self.spawn_greenlet("rec", recursive_a, n - 1)
            return g.get()

        yappi.set_clock_type("cpu")

        def driver():

            to_run = [
                (recursive_a, (5,)),
                (recursive_a, (5,))
            ]

            ts = []
            for idx, (func, args) in enumerate(to_run):
                t = self.spawn_thread("%s_%d" % (func.__name__, idx), func, *args)
                ts.append(t)

            recursive_a(6)

            for t in ts:
                t.join()

        yappi.start(profile_greenlets=False)

        driver()

        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        tests/test_gevent.py:359 driver       1      0.000061  0.101845  0.101845
        tests/test_gevent.py:335 recursive_a  1      0.000262  0.100619  0.100619
        ../yappi/tests/utils.py:126 burn_cpu  1      0.000000  0.100082  0.100082
        '''
        self.assert_traces_almost_equal(t1, traces)
        gstats = yappi.get_greenlet_stats()
        r2 = '''
        Main           1      0.101944  1
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

    def test_default_ctx_name_callback(self):

        # Set context backend to confgiure default callbacks
        yappi.set_context_backend("greenlet")


        class GreenletA(gevent.Greenlet):
            pass

        def thread_a():
            g = GreenletA(a)
            g.start()
            g.get()

        def a():
            burn_cpu(0.1)

        def thread_b():
            g = GreenletB(b)
            g.start()
            g.get()

        class GreenletB(gevent.Greenlet):
            pass

        def b():
            burn_cpu(0.2)

        def driver():
            tA = self.spawn_thread("a", thread_a)
            tB = self.spawn_thread("b", thread_b)
            tA.join()
            tB.join()

        yappi.start()
        driver()
        yappi.stop()

        gstats = yappi.get_greenlet_stats()
        r2 = '''
        GreenletB      7      0.200104  9
        GreenletA      4      0.100082  8
        '''
        self.assert_ctx_stats_almost_equal(r2, gstats)

if __name__ == '__main__':
    unittest.main()
