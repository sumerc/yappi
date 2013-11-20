import yappi
stats = yappi.YFuncStats().add("a.1").add("a.2").add("a.3")
stats.print_all()
stats.save("merged.pstat", "pstat")