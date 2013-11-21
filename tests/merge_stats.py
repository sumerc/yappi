import yappi
stats = yappi.YFuncStats().add("a.1").add("a.2").add("a.3")
stats.sort("tsub", "desc").print_all()
#stats.save("merged.pstat", "pstat")
#stats.print_all()
#yappi.start()
#yappi.get_func_stats().print_all()
#yappi.get_thread_stats().print_all()