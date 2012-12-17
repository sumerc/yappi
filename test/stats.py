import yappi

def foo():
    for i in range(1000000): pass
def bar():
    for i in range(1000000): pass

yappi.start()
foo()
yappi.stop()
fstats = yappi.get_func_stats()
fstats.save("foo1")
yappi.clear_stats()

yappi.start()
bar()
foo()
yappi.stop()
fstats = yappi.get_func_stats()
fstats.save("foobar1")
yappi.clear_stats()

yfs = yappi.YFuncStats()
yfs.add("foo1")
yfs.add("foobar1")
yappi.print_func_stats(stats=yfs)
