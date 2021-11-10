import unittest
import yappi
import asyncio
import threading
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io


@asyncio.coroutine
def async_sleep(sec):
    yield from asyncio.sleep(sec)


class SingleThreadTests(YappiUnitTestCase):

    def test_issue58(self):

        @asyncio.coroutine
        def mt(d):
            t = asyncio.Task(async_sleep(3 + d))
            yield from async_sleep(3)
            yield from t

        yappi.set_clock_type('wall')

        with yappi.run():
            asyncio.get_event_loop().run_until_complete(mt(-2))
        r1 = '''
        async_sleep 2      0  4.005451  2.002725
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)
        yappi.clear_stats()

        with yappi.run():
            asyncio.get_event_loop().run_until_complete(mt(1))
        r1 = '''
        async_sleep 2      0  7.006886  3.503443
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

    def test_recursive_coroutine(self):

        @asyncio.coroutine
        def a(n):
            if n <= 0:
                return
            yield from async_sleep(0.1)
            burn_cpu(0.1)
            yield from a(n - 1)
            yield from a(n - 2)

        yappi.set_clock_type("cpu")
        yappi.start()
        asyncio.get_event_loop().run_until_complete(a(3))
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:11 a  9/1    0.000124  0.400667  0.044519
        ../yappi/tests/utils.py:126 burn_cpu  4      0.000000  0.400099  0.100025
        async_sleep                           4      0.000000  0.000444  0.000111
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

    def test_basic_old_style(self):

        @asyncio.coroutine
        def a():
            yield from async_sleep(0.1)
            burn_io(0.1)
            yield from async_sleep(0.1)
            burn_io(0.1)
            yield from async_sleep(0.1)
            burn_cpu(0.3)

        yappi.set_clock_type("wall")
        yappi.start(builtins=True)
        asyncio.get_event_loop().run_until_complete(a())
        asyncio.get_event_loop().run_until_complete(a())
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
        asyncio.get_event_loop().run_until_complete(a())
        asyncio.get_event_loop().run_until_complete(a())
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

        @asyncio.coroutine
        def a():
            yield from async_sleep(0.3)
            burn_cpu(0.4)

        @asyncio.coroutine
        def b():
            yield from a()

        @asyncio.coroutine
        def recursive_a(n):
            if not n:
                return
            burn_io(0.3)
            yield from async_sleep(0.3)
            yield from recursive_a(n - 1)

        tlocal = threading.local()

        def tag_cbk():
            try:
                return tlocal._tag
            except:
                return -1

        yappi.set_clock_type("wall")
        tlocal._tag = 0
        yappi.set_tag_callback(tag_cbk)

        def _thread_event_loop(loop, tag):
            tlocal._tag = tag
            asyncio.set_event_loop(loop)
            loop.run_forever()

        _TCOUNT = 3
        _ctag = 1

        ts = []
        for i in range(_TCOUNT):
            _loop = asyncio.new_event_loop()
            t = threading.Thread(target=_thread_event_loop, args=(_loop, _ctag))
            t._loop = _loop
            t.start()

            ts.append(t)
            _ctag += 1

        @asyncio.coroutine
        def stop_loop():
            asyncio.get_event_loop().stop()

        @asyncio.coroutine
        def driver():
            futs = []
            fut = asyncio.run_coroutine_threadsafe(a(), ts[0]._loop)
            futs.append(fut)
            fut = asyncio.run_coroutine_threadsafe(recursive_a(5), ts[1]._loop)
            futs.append(fut)
            fut = asyncio.run_coroutine_threadsafe(b(), ts[2]._loop)
            futs.append(fut)
            for fut in futs:
                fut.result()

            # stop asyncio loops in threads
            for t in ts:
                asyncio.run_coroutine_threadsafe(stop_loop(), t._loop)

        yappi.start()
        asyncio.get_event_loop().run_until_complete(driver())
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
