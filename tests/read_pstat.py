import pstats
p = pstats.Stats('merged.pstat')
p.strip_dirs().sort_stats(-1).print_stats()