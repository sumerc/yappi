import unittest
import yappi
import asyncio
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io


class SingleThreadTests(YappiUnitTestCase):

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
        ..p/yappi/tests/test_asyncio.py:11 a  9/1    0.000953  0.404821  0.044980
        ../yappi/tests/utils.py:125 burn_cpu  4      0.163852  0.400735  0.100184
        ..thon3.7/asyncio/tasks.py:582 sleep  4      0.000637  0.003133  0.000783
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
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.000577  1.631672  0.815836
        ..thon3.7/asyncio/tasks.py:582 sleep  6      0.622954  0.629176  0.104863
        ../yappi/tests/utils.py:125 burn_cpu  2      0.257561  0.600316  0.300158
        ..p/yappi/tests/utils.py:134 burn_io  4      0.000447  0.401603  0.100401
        time.sleep                            4      0.401156  0.401156  0.100289
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
        ..p/yappi/tests/test_asyncio.py:43 a  2      0.001122  0.610890  0.305445
        ../yappi/tests/utils.py:125 burn_cpu  2      0.263175  0.600361  0.300180
        ..thon3.7/asyncio/tasks.py:582 sleep  6      0.001472  0.008230  0.001372
        time.sleep                            4      0.000672  0.000672  0.000168
        '''
        self.assert_traces_almost_equal(r1, stats)


class MultiThreadTests(YappiUnitTestCase):

    def test_basic(self):
        pass

    def test_recursive_coroutine(self):
        pass

    def test_same_coroutine_call_from_different_threads(self):
        pass


if __name__ == '__main__':
    unittest.main()
