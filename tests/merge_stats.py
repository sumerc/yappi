import yappi
stats = yappi.YFuncStats().add("a.1").add("a.2").add("a.3")
stats.sort("tsub", "desc").print_all()
stats.save("a.merged", "pstat")
#stats.save("merged.pstat", "pstat")
#stats.print_all()
#yappi.start()
#yappi.get_func_stats().print_all()
#yappi.get_thread_stats().print_all()
import pstats
#p = pstats.Stats("a.1").add("a.2", "a.3")
p = pstats.Stats("a.merged")
p.strip_dirs().sort_stats(-1).print_stats()