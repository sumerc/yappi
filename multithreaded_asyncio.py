import asyncio
from threading import Thread

loop = asyncio.new_event_loop()


def f(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()


t = Thread(target=f, args=(loop, ))
t.start()


@asyncio.coroutine
def g():
    print('g start')
    yield from asyncio.sleep(0.1)
    print(id(asyncio.get_event_loop()))
    yield from asyncio.sleep(0.1)
    print('g end')


async def main():
    print("main loop:", id(asyncio.get_event_loop()))
    f1 = asyncio.run_coroutine_threadsafe(g(), loop)
    f2 = asyncio.run_coroutine_threadsafe(g(), loop)
    await asyncio.sleep(1.0)
    print("ended")
    #t1 = asyncio.Task(g())
    #t2 = asyncio.Task(g())
    #print(t1.)
    #await asyncio.sleep(3.0)


import yappi
yappi.set_clock_type("wall")
yappi.start()
asyncio.run(main())
yappi.get_func_stats().print_all()
