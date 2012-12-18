import yappi

def foo():
    for i in range(1000000): pass
def foo2():
    for i in range(1000000): pass
def bar():
    for i in range(1000000): pass
def bar2():
    for i in range(1000000): pass
def foo3():
    for i in range(1000000): pass
    
yappi.start()
foo()
foo2()
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
yappi.print_func_stats(stats=yfs, sort_type=yappi.SORTTYPE_TTOT)

yappi.start()
bar()
foo()
foo()
bar2()
bar()
bar2()
foo2()
foo3()
yappi.stop()
fstats = yappi.print_func_stats(sort_type=yappi.SORTTYPE_TTOT)
fstats = yappi.print_thread_stats()
yappi.clear_stats()
