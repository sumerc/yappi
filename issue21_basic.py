import asyncio
import time
from contextvars import ContextVar

import yappi


async def func_to_profile(n=2):
    if not n:
        return
    #for i in range(100000):
    #    pass
    await asyncio.sleep(1)
    #for i in range(1000000):
    #    pass
    await asyncio.sleep(1)
    #await asyncio.sleep(1)
    await func_to_profile(n - 1)


async def main():
    yappi.set_clock_type("wall")
    yappi.start()
    _ = await asyncio.gather(
        *[
            func_to_profile(),
            func_to_profile(),
            func_to_profile(),
            func_to_profile()
        ]
    )
    yappi.stop()
    yappi.get_func_stats().print_all()


if __name__ == '__main__':
    asyncio.run(main())
