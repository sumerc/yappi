import asyncio
import time
import unittest
from contextvars import ContextVar

import utils
import yappi
from utils import YappiUnitTestCase


class SingleEventLoopTest(YappiUnitTestCase):

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
        def mytask():
            yield from asyncio.sleep(0.1)
            time.sleep(0.1)
            yield from asyncio.sleep(0.1)

        yappi.set_clock_type("wall")

        yappi.set_context_name_callback(lambda: "1")
        yappi.start()
        asyncio.run(mytask())
        yappi.stop()
        yappi.set_context_name_callback(lambda: "2")
        yappi.start()
        asyncio.run(mytask())
        yappi.stop()

        yappi.get_func_stats(filter={"ctx_name": "1"}).print_all()
        # print(stats)
        # print(">>>>>>")


class MultipleEventLoopTest(YappiUnitTestCase):

    def test_basic(self):
        pass

    def test_recursive_coroutine(self):
        pass

    def test_same_coroutine_call_from_different_threads(self):
        pass

    def test_multiple_event_loops_in_same_thread(self):
        pass


async_context_id = ContextVar('async_context_id')
async_context_id.set(-1)


def get_async_context_id():
    try:
        return async_context_id.get()
    except LookupError:
        return -2


class AsyncUsage(utils.YappiUnitTestCase):
    task_count = 5
    duration = 0.1

    def test_async_cpu(self):
        task_count = 5
        yappi.set_clock_type("cpu")
        yappi.set_context_id_callback(get_async_context_id)
        asyncio.run(self._run_async_calls())
        for i in range(task_count):
            fstats = yappi.get_func_stats(filter={"ctx_id": i, "name": "sleep_for"})
            stats = fstats.pop()
            self.assertEqual(stats.ncall, 2)  # Change to 1 if context switches should not count as calls
            self.assertLessEqual(stats.ttot, self.duration * 0.01)

    def test_async_wall(self):
        yappi.set_clock_type("wall")
        yappi.set_context_id_callback(get_async_context_id)
        asyncio.run(self._run_async_calls())
        for i in range(self.task_count):
            fstats = yappi.get_func_stats(filter={"ctx_id": i, "name": "sleep_for"})
            stats = fstats.pop()
            self.assertEqual(stats.ncall, 2)  # Change to 1 if context switches should not count as calls
            self.assertGreaterEqual(stats.ttot, self.duration)

    async def _run_async_calls(self):
        async def await_with_context_id(context_id, awaitable):
            async_context_id.set(context_id)
            return await awaitable

        async def sleep_for(time: float):
            await asyncio.sleep(time)

        yappi.start()
        tasks = [await_with_context_id(i, sleep_for(self.duration)) for i in range(self.task_count)]
        await asyncio.gather(*tasks)
        yappi.stop()


if __name__ == '__main__':
    unittest.main()
