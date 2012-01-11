'''

 yappi.py
 Yet Another Python Profiler

 Sumer Cip 2011

'''
import sys
import threading
import _yappi
from collections import namedtuple

__all__ = ['start', 'stop', 'enum_stats', 'print_stats', 'clear_stats', 'is_running', 'get_stats']

SORTTYPE_NAME = 0
SORTTYPE_NCALL = 1
SORTTYPE_TTOTAL = 2
SORTTYPE_TSUB = 3
SORTTYPE_TAVG = 4
SORTORDER_ASCENDING = 0
SORTORDER_DESCENDING = 1
SHOW_ALL = 0

class StatString:
    
    _s = ""
    _TRAIL_DOT = ".."
    
    def __init__(self, s):        
        self._s = str(s)
    
    def left_trailing_dots(self, length):
        if len(self._s) > length:
            self._s = self._s[-length:]
            return self._TRAIL_DOT + self._s[len(self._TRAIL_DOT):]
        else:
            return self._s + " " * (length - len(self._s))
        
    def right_trailing_dots(self, length):
        if len(self._s) > length:
            self._s = self._s[length:]
            return self._s[:-len(self._TRAIL_DOT)] + self._TRAIL_DOT
        else:
            return self._s + (" " * (length - len(self._s)))
        
YFuncStatEntry = namedtuple('YFuncStatEntry', 'name ncall ttot tsub tavg')
YThreadStatEntry = namedtuple('YThreadStatEntry', 'name id last_func sched_count')

class YStats:
    
    def __init__(self, sort_type, sort_order, limit):
        
        self.func_stats = [] 
        self.thread_stats = []
    
        self._sort_type = sort_type
        self._sort_order = sort_order
        self._limit = limit
    
    def sort(self):
        self.func_stats.sort(key=lambda stat: stat[self._sort_type], 
            reverse=(self._sort_order==SORTORDER_DESCENDING))
    
    def limit(self):
        if self._limit != SHOW_ALL:
            self.func_stats = self.func_stats[:self._limit]
        
    def func_enumerator(self, stat_entry):
        tavg = stat_entry[2]/stat_entry[1]
        fstat = YFuncStatEntry(*(stat_entry+(tavg,)))
        if "yappi.py" not in fstat.name: # TODO : decide to exclude this?
            self.func_stats.append(fstat)
        
    def thread_enumerator(self, stat_entry):
        tstat = YThreadStatEntry(*stat_entry)
        self.thread_stats.append(tstat)
        
'''
 __callback will only be called once per-thread. _yappi will detect
 the new thread and changes the profilefunc param of the ThreadState
 structure. This is an internal function please don't mess with it.
'''
def __callback(frame, event, arg):
    _yappi.profile_event(frame, event, arg)
    return __callback
    
def is_running():
    return bool(_yappi.is_running())


def start(builtins = False):
    '''
    Args:
    builtins: If set true, then builtin functions are profiled too.
    timing_sample: will cause the profiler to do timing measuresements
                   according to the value. Will increase profiler speed but
                   decrease accuracy.
    '''
    threading.setprofile(__callback)
    _yappi.start(builtins)
    
    
def get_stats(sorttype=SORTTYPE_NCALL, sortorder=SORTORDER_DESCENDING, limit=SHOW_ALL):
    stats = YStats(sorttype, sortorder, limit)
    enum_stats(stats.func_enumerator)
    enum_thread_stats(stats.thread_enumerator)
    stats.sort()
    stats.limit()
    return stats

def stop():
    '''
    Stop profiling.
    '''
    threading.setprofile(None)
    _yappi.stop()

def enum_stats(fenum):
    _yappi.enum_stats(fenum)

def enum_thread_stats(fenum):
    _yappi.enum_thread_stats(fenum)

def print_stats(sorttype=SORTTYPE_NCALL, sortorder=SORTORDER_DESCENDING, limit=SHOW_ALL):
    stats = get_stats(sorttype, sortorder, limit)
    
    FUNC_NAME_LEN = 35
    CALLCOUNT_LEN = 12
    TIME_COLUMN_LEN = 7 # 0.00000, 12345.9
    COLUMN_GAP = 2
    THREAD_NAME_LEN = 13
    THREAD_ID_LEN = 12
    THREAD_SCHED_CNT_LEN = 12
    
    print ""
    print  "name                                 #n            tsub     ttot     tavg"
    for stat in stats.func_stats: 
        sys.stdout.write(StatString(stat.name).left_trailing_dots(FUNC_NAME_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString(stat.ncall).right_trailing_dots(CALLCOUNT_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString("%0.5f" % stat.tsub).right_trailing_dots(TIME_COLUMN_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString("%0.5f" % stat.ttot).right_trailing_dots(TIME_COLUMN_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString("%0.5f" % stat.tavg).right_trailing_dots(TIME_COLUMN_LEN))
        print ""
        
    print ""
    print "name           tid           fname                                scnt"
    for stat in stats.thread_stats: 
        sys.stdout.write(StatString(stat.name).left_trailing_dots(THREAD_NAME_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString(stat.id).right_trailing_dots(THREAD_ID_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString(stat.last_func).left_trailing_dots(FUNC_NAME_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        sys.stdout.write(StatString(stat.sched_count).right_trailing_dots(THREAD_SCHED_CNT_LEN))
        sys.stdout.write(" " * COLUMN_GAP)
        print ""
        
def clear_stats():
    _yappi.clear_stats()

def main():
    import os, sys
    from optparse import OptionParser
    usage = "yappi.py [-b] [scriptfile] args ..."
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    parser.add_option("-b", "--builtins",
                  action="store_true", dest="profile_builtins", default=False,
                  help="Profiles builtin functions when set. [default: False]") 
    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)

    (options, args) = parser.parse_args()
    sys.argv[:] = args

    if (len(sys.argv) > 0):
        sys.path.insert(0, os.path.dirname(sys.argv[0]))
        start(options.profile_builtins, options.timing_sample)
        execfile(sys.argv[0])
        stop()
        print_stats() # TODO: accept params for this
    else:
        parser.print_usage()
    return parser
    
if __name__ == "__main__":
    main()


