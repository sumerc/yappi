import sys
import unittest
import asyncio
import contextvars
import functools
import time
import os
import utils
import yappi

async_context_id = contextvars.ContextVar('async_context_id')
async_context_id.set(-1)


def get_async_context_id():
    try:
        return async_context_id.get()
    except LookupError:
        return -2


async def run_in_threadpool(copy_contextvars, func, *args, **kwargs):
    """Based on the starlette function of the same name"""
    loop = asyncio.get_event_loop()
    if copy_contextvars:
        # Ensure we run in the same context
        child = functools.partial(func, *args, **kwargs)
        context = contextvars.copy_context()
        func = context.run
        args = (child, )
    elif kwargs:
        func = functools.partial(func, **kwargs)
    return await loop.run_in_executor(None, func, *args)


class AsyncUsage(utils.YappiUnitTestCase):
    task_count = 5
    context_switch_count = 2
    duration = 0.2
    task_to_profile_name = "task_to_profile"

    def test_async_cpu(self):
        ttots = self.profile_tasks("cpu")
        for ttot in ttots:
            # TODO: What is the underlying assumption here by 0.2, I think
            # this has implicit trust on machine speed. We need to change this
            self.assertLessEqual(ttot, self.duration * 0.2)

    # TODO: fix this
    @unittest.skipIf(os.name == "nt", "do not run on Windows")
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
        fstats = yappi.get_func_stats(
            filter={"name": self.task_to_profile_name}
        )
        #fstats.print_all()
        stats = fstats.pop()
        #self.assertEqual(
        #    stats.ncall, self.task_count * self.context_switch_count
        #)

        averaged_times = [
            stats.ttot / self.task_count for _ in range(self.task_count)
        ]
        return averaged_times

    def get_tasks(self):
        return [
            self.task_to_profile(self.duration) for _ in range(self.task_count)
        ]

    @staticmethod
    async def task_to_profile(duration: float):
        await asyncio.sleep(duration)


class ContextVarsMixin:
    task_count: int
    duration: float
    task_to_profile_name: str
    context_switch_count: int

    async def profile_tasks_coroutine(self):
        yappi.set_tag_callback(get_async_context_id)
        await super().profile_tasks_coroutine()

    def get_profiling_outputs(self):
        ttots = []
        for i in range(self.task_count):
            fstats = yappi.get_func_stats(
                filter={
                    "tag": i,
                    "name": self.task_to_profile_name
                }
            )
            stats = fstats.pop()
            #self.assertEqual(stats.ncall, self.context_switch_count)
            ttots.append(stats.ttot)
        return ttots

    def get_tasks(self):

        async def await_with_context_id(context_id, awaitable):
            async_context_id.set(context_id)
            return await awaitable

        return [
            await_with_context_id(i, self.task_to_profile(self.duration))
            for i in range(self.task_count)
        ]


class ThreadTaskMixin:
    run_in_threadpool_copy_contextvars = False
    task_to_profile_name = "_task_in_thread"
    context_switch_count = 1

    async def task_to_profile(self, duration: float):
        await run_in_threadpool(
            self.run_in_threadpool_copy_contextvars, self._task_in_thread,
            duration
        )

    @staticmethod
    def _task_in_thread(duration: float):
        time.sleep(duration)


class AsyncUsageWithContextvars(ContextVarsMixin, AsyncUsage):
    pass


class AsyncUsageThreaded(ThreadTaskMixin, AsyncUsage):
    pass


class AsyncUsageThreadedWithContextvars(
    ThreadTaskMixin, ContextVarsMixin, AsyncUsage
):
    run_in_threadpool_copy_contextvars = True


class AsyncUsageThreadedWithContextvarsSelfContained(utils.YappiUnitTestCase):
    task_count = 5
    context_switch_count = 1
    duration = 0.2
    task_to_profile_name = "_task_in_thread"

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
        yappi.set_tag_callback(get_async_context_id)
        yappi.start()
        tasks = self.get_tasks()
        await asyncio.gather(*tasks)
        yappi.stop()

    def get_profiling_outputs(self):
        ttots = []
        for i in range(self.task_count):
            fstats = yappi.get_func_stats(
                filter={
                    "tag": i,
                    "name": self.task_to_profile_name
                }
            )
            stats = fstats.pop()
            #self.assertEqual(stats.ncall, self.context_switch_count)
            ttots.append(stats.ttot)
        return ttots

    def get_tasks(self):

        async def await_with_context_id(context_id, awaitable):
            async_context_id.set(context_id)
            return await awaitable

        return [
            await_with_context_id(i, self.task_to_profile(self.duration))
            for i in range(self.task_count)
        ]

    async def task_to_profile(self, duration: float):
        await run_in_threadpool(
            copy_contextvars=True, func=self._task_in_thread, duration=duration
        )

    @staticmethod
    def _task_in_thread(duration: float):
        time.sleep(duration)
