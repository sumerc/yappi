def foo():
    import time
    time.sleep(1.0)

def bar():
    foo()
    foo()


import sys
import yappi
yappi.start()
bar()
yappi.print_stats()

import cProfile
cProfile.run('bar()')

