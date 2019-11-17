import asyncio
import time
from contextvars import ContextVar

import yappi

yappi_request_id = ContextVar('yappi_request_id')
yappi_request_id.set(-1)


def get_context_id() -> int:
    try:
        return yappi_request_id.get()
    except LookupError:
        return -2


yappi.set_context_id_callback(get_context_id)


async def _wrapper(context_id: int) -> float:
    yappi_request_id.set(context_id)

    assert yappi_request_id.get() == context_id

    return await func_to_profile()


async def func_to_profile() -> float:

    start = time.time()
    await asyncio.sleep(1)
    end = time.time()

    return end - start


yappi.set_clock_type("wall")
yappi.start()


async def main():
    context_ids = [1, 2, 3]
    tasks = [_wrapper(i) for i in context_ids]
    actual_durations = await asyncio.gather(*tasks)
    yappi_durations = [
        yappi.get_func_stats({
            "name": "func_to_profile",
            "ctx_id": i
        }).pop().ttot for i in context_ids
    ]
    for context_id, actual_duration, yappi_duration in zip(
        context_ids, actual_durations, yappi_durations
    ):
        print(f"Task {context_id}:")
        print(f"    Actual wall time: {actual_duration * 1000:>8.3f}ms")
        print(f"     Yappi wall time: {yappi_duration * 1000:>8.3f}ms")


if __name__ == '__main__':
    asyncio.run(main())
