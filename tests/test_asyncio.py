import unittest
import time
import yappi
import asyncio
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
        #print(stats)
        #print(">>>>>>")


class MultipleEventLoopTest(YappiUnitTestCase):

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
