import yappi
from test_utils import assert_raises_exception, test_passed

def foo():
    for i in range(1000000): pass
def foo1():
    for i in range(1000000): pass
def foo2():
    for i in range(1000000): pass
def bar():
    for i in range(1000000): pass
def bar1():
    for i in range(1000000): pass
def bar2():
    for i in range(1000000): pass
def foo3():
    for i in range(1000000): pass
    
def foo_child1():
    foo1()
    bar1()
def foo_child2():
    foo2()
    bar2()
    
def test1():
    bar()
    foo()
    foo_child1()
    foo_child2()

yappi.start(profile_threads=False)
foo()
foo2()
foo_child1()
yappi.stop()
fstats1 = yappi.get_func_stats()
fstats1.print_all()
fstats1.save("foo1")
yappi.clear_stats()

#yappi.set_clock_type("waLL")
yappi.start(builtins=True, profile_threads=False)
test1()
yappi.stop()
fstats2 = yappi.get_func_stats()
fstats2.save("foobar1")
yappi.clear_stats()

yfs = yappi.YFuncStats()
yfs.add("foo1").add('foobar1')
yfs.sort(sort_type=yappi.SORTTYPE_TTOT).print_all() 
yfs.save('callgrind.out', 'callgrind')
#foobar_stat = yfs.find_by_name('test1')
#yfs.debug_print()
for stat in yfs:
    fstatin1 = fstats1.find_by_full_name(stat.full_name)
    fstatin2 = fstats2.find_by_full_name(stat.full_name)
    
        

