def fib(n):
   if n > 1:
       return fib(n-1) + fib(n-2)
   else:
       return n
       
       
import yappi
yappi.start()
fib(22)
yappi.print_stats()

import cProfile
cProfile.run('fib(22)')