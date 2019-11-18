import asyncio
import yappi
import time


def mygenerator(n):
    while (n):
        yield n
        n -= 1


# async generator
async def ticker(n):
    for i in range(n):
        yield i
        #await asyncio.sleep(1.0)


@asyncio.coroutine
def old_style_coroutine():
    yield from asyncio.sleep(0.1)


async def myasyncfunc(n=2):
    if n == 3:
        time.sleep(0.1)
        return
    if not n:
        return
    await asyncio.sleep(0.1)
    time.sleep(0.1)
    await old_style_coroutine()

    async for i in ticker(2):
        print("giter", i)

    await myasyncfunc(n - 1)
    await myasyncfunc(3)


def normal_rec(n=2):
    if n == 3:
        return
    if not n:
        return
    normal_rec(n - 1)
    normal_rec(3)


#yappi.set_clock_type("wall")
yappi.start(builtins=True)
for i in mygenerator(5):
    print(i)
t0 = time.time()
asyncio.run(myasyncfunc())
asyncio.run(myasyncfunc())
normal_rec()
normal_rec()
yappi.stop()
traces = yappi.get_func_stats()
for t in traces:
    if t.name == 'myasyncfunc':
        for c in t.children:
            print(c.module, c.name, c.ttot)
traces.print_all()
