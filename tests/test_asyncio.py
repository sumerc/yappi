import unittest
import time
import yappi
import asyncio
from utils import YappiUnitTestCase, find_stat_by_name


def burn_cpu(sec):
    t0 = time.time()
    elapsed_ms = 0
    while (elapsed_ms < sec):
        for _ in range(1000):
            pass
        elapsed_ms = time.time() - t0


def burn_io(sec):
    time.sleep(sec)


class SingleThread(YappiUnitTestCase):

    def test_recursive_coroutine(self):
        pass

    def test_async_context_managers(self):
        pass

    def test_naive_generators(self):
        pass

    def test_async_generators(self):
        pass

    def test_basic_new_style(self):
        pass

    def test_basic_old_style(self):

        @asyncio.coroutine
        def a():
            yield from asyncio.sleep(0.1)
            burn_io(0.1)
            yield from asyncio.sleep(0.1)
            burn_io(0.1)
            yield from asyncio.sleep(0.1)
            burn_cpu(0.3)

        yappi.set_clock_type("wall")
        yappi.start(builtins=True)
        asyncio.run(a())
        asyncio.run(a())
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:40 a  2      0.000000  1.600000  0.803634
        ..thon3.7/asyncio/tasks.py:582 sleep  6      0.600000  0.600000  0.100855
        ..i/tests/test_asyncio.py:8 burn_cpu  2      0.600000  0.600000  0.300011
        ..i/tests/test_asyncio.py:17 burn_io  4      0.000000  0.400000  0.100490
        time.sleep                            4      0.400000  0.400000  0.100481
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)


class MultiThread(YappiUnitTestCase):

    def test_basic(self):
        pass

    def test_recursive_coroutine(self):
        pass

    def test_same_coroutine_call_from_different_threads(self):
        pass

    def test_multiple_event_loops_in_same_thread(self):
        pass


if __name__ == '__main__':
    unittest.main()
