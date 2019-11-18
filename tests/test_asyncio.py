import asyncio
import contextvars
import functools
import time
import unittest

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


async_context_id = contextvars.ContextVar('async_context_id')
async_context_id.set(-1)


def get_async_context_id():
    try:
        return async_context_id.get()
    except LookupError:
        return -2


class AsyncUsage(utils.YappiUnitTestCase):
    task_count = 5
    context_switch_count = 2
    duration = 0.1
    task_to_profile_name = "task_to_profile"

    def test_async_cpu(self):
        ttots = self.profile_tasks("cpu")
        for ttot in ttots:
            self.assertLessEqual(ttot, self.duration * 0.1)

    def test_async_wall(self):
        ttots = self.profile_tasks("wall")
        for ttot in ttots:
            self.assertGreaterEqual(ttot, self.duration)

    def profile_tasks(self, clock_type):
        yappi.set_clock_type(clock_type)
        asyncio.run(self.profile_tasks_coroutine())
        return self.get_profiling_outputs()

    async def profile_tasks_coroutine(self):
        yappi.start()
        tasks = self.get_tasks()
        await asyncio.gather(*tasks)
        yappi.stop()

    def get_profiling_outputs(self):
        fstats = yappi.get_func_stats(filter={"name": self.task_to_profile_name})
        stats = fstats.pop()
        self.assertEqual(stats.ncall, self.task_count * self.context_switch_count)

        averaged_times = [stats.ttot / self.task_count for _ in range(self.task_count)]
        return averaged_times

    def get_tasks(self):
        return [self.task_to_profile(self.duration) for _ in range(self.task_count)]

    @staticmethod
    async def task_to_profile(duration: float):
        await asyncio.sleep(duration)


class ContextVarsMixin:
    task_count: int
    duration: float
    task_to_profile_name: str
    context_switch_count: int

    async def profile_tasks_coroutine(self):
        yappi.set_context_id_callback(get_async_context_id)
        await super().profile_tasks_coroutine()

    def get_profiling_outputs(self):
        ttots = []
        for i in range(self.task_count):
            fstats = yappi.get_func_stats(filter={"ctx_id": i, "name": self.task_to_profile_name})
            stats = fstats.pop()
            self.assertEqual(stats.ncall, self.context_switch_count)
            ttots.append(stats.ttot)
        return ttots

    def get_tasks(self):
        async def await_with_context_id(context_id, awaitable):
            async_context_id.set(context_id)
            return await awaitable

        return [await_with_context_id(i, self.task_to_profile(self.duration)) for i in range(self.task_count)]


class ThreadTaskMixin:
    run_in_threadpool_copy_contextvars = False
    task_to_profile_name = "_task_in_thread"
    context_switch_count = 1

    async def task_to_profile(self, duration: float):
        await run_in_threadpool(self.run_in_threadpool_copy_contextvars, self._task_in_thread, duration)

    @staticmethod
    def _task_in_thread(duration: float):
        time.sleep(duration)


class AsyncUsageWithContextvars(ContextVarsMixin, AsyncUsage):
    pass


class AsyncUsageThreaded(ThreadTaskMixin, AsyncUsage):
    pass


class AsyncUsageThreadedWithContextvars(ThreadTaskMixin, ContextVarsMixin, AsyncUsage):
    run_in_threadpool_copy_contextvars = True


async def run_in_threadpool(copy_contextvars, func, *args, **kwargs):
    """Based on the starlette function of the same name"""
    loop = asyncio.get_event_loop()
    if copy_contextvars:
        # Ensure we run in the same context
        child = functools.partial(func, *args, **kwargs)
        context = contextvars.copy_context()
        func = context.run
        args = (child,)
    elif kwargs:
        func = functools.partial(func, **kwargs)
    return await loop.run_in_executor(None, func, *args)

if __name__ == '__main__':
    unittest.main()
