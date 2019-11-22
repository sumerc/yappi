import unittest
import yappi
import asyncio
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io


class SingleThread(YappiUnitTestCase):

    def test_recursive_coroutine(self):

        async def a(n):
            if n <= 0:
                return
            await asyncio.sleep(0.1)
            burn_cpu(0.1)
            await a(n - 1)
            await a(n - 2)

        yappi.set_clock_type("cpu")
        yappi.start()
        asyncio.run(a(3))
        yappi.stop()

        r1 = '''
        ..p/yappi/tests/test_asyncio.py:25 a  9/1    0.000081  0.400395  0.044488
        ..i/tests/test_asyncio.py:8 burn_cpu  4      0.381794  0.400035  0.100009
        ..thon3.7/asyncio/tasks.py:582 sleep  4      0.000100  0.000279  0.000070
        '''
        stats = yappi.get_func_stats()
        self.assert_traces_almost_equal(r1, stats)

    def test_async_context_managers(self):
        pass

    def test_naive_generators(self):
        pass

    def test_async_generators(self):
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

        yappi.clear_stats()
        yappi.set_clock_type("cpu")
        yappi.start(builtins=True)
        asyncio.run(a())
        asyncio.run(a())
        yappi.stop()
        stats = yappi.get_func_stats()
        r1 = '''
        ..p/yappi/tests/test_asyncio.py:51 a  2      0.000188  0.601679  0.300839
        ..i/tests/test_asyncio.py:8 burn_cpu  2      0.572000  0.599999  0.300000
        ..thon3.7/asyncio/tasks.py:582 sleep  6      0.000232  0.001143  0.000190
        ..i/tests/test_asyncio.py:17 burn_io  4      0.000059  0.000349  0.000087
        time.sleep                            4      0.000290  0.000290  0.000073
        '''
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
