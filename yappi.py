'''
 yappi.py
 Yet Another Python Profiler

 Sumer Cip 2012
'''
import os
import sys
import threading
import _yappi
import pickle

class YappiError(Exception): pass

__all__ = ['start', 'stop', 'enum_func_stats', 'enum_thread_stats', 'print_func_stats',
           'print_thread_stats', 'get_func_stats', 'get_thread_stats', 'clear_stats', 'is_running',
           'clock_type', 'mem_usage']

CRLF = '\n'
COLUMN_GAP = 2
TIME_COLUMN_LEN = 8 # 0.000000, 12345.98, precision is microsecs

SORTTYPE_NAME = 0
SORTTYPE_NCALL = 3
SORTTYPE_TTOT = 4
SORTTYPE_TSUB = 5
SORTTYPE_TAVG = 8
SORTTYPE_THREAD_NAME = 0
SORTTYPE_THREAD_ID = 1
SORTTYPE_THREAD_TTOT = 3
SORTTYPE_THREAD_SCHEDCNT = 4

SORTORDER_ASC = 0
SORTORDER_DESC = 1

SHOW_ALL = 0

def validate_func_sorttype(sort_type):
    if sort_type not in [SORTTYPE_NAME, SORTTYPE_NCALL, SORTTYPE_TTOT, SORTTYPE_TSUB, SORTTYPE_TAVG]:
        raise YappiError("Invalid SortType parameter.[%d]" % (sort_type))

def validate_thread_sorttype(sort_type):
    if sort_type not in [SORTTYPE_THREAD_NAME, SORTTYPE_THREAD_ID, SORTTYPE_THREAD_TTOT, SORTTYPE_THREAD_SCHEDCNT]:
        raise YappiError("Invalid SortType parameter.[%d]" % (sort_type))
        
def validate_sortorder(sort_order):
    if sort_order not in [SORTORDER_ASC, SORTORDER_DESC]:
        raise YappiError("Invalid SortOrder parameter.[%d]" % (sort_order))

class StatString:
    """
    Class to prettify/trim a profile result column.
    """

    _s = ""
    _TRAIL_DOT = ".."

    def __init__(self, s):
        self._s = str(s)

    def ltrim(self, length):
        if len(self._s) > length:
            self._s = self._s[-length:]
            return self._TRAIL_DOT + self._s[len(self._TRAIL_DOT):]
        else:
            return self._s + " " * (length - len(self._s))

    def rtrim(self, length):
        if len(self._s) > length:
            self._s = self._s[:length]
            return self._s[:-len(self._TRAIL_DOT)] + self._TRAIL_DOT
        else:
            return self._s + (" " * (length - len(self._s)))

class YStat(dict):
    """
    Class to hold a profile result line in a dict object, which all items can also be accessed as
    instance attributes where their attribute name is the given key. Mimicked NamedTuples.
    """
    _KEYS = () 
    
    def __init__(self, values):
        super(YStat, self).__init__()
        
        assert len(self._KEYS) == len(values)
        for i in range(len(self._KEYS)):
            setattr(self, self._KEYS[i], values[i])
            self[i] = values[i]

class YFuncStat(YStat):
    _KEYS = ('name', 'module', 'lineno', 'ncall', 'ttot', 'tsub', 'index', 'children', 'tavg', 'full_name')
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.full_name == other.full_name
         
class YThreadStat(YStat):
    _KEYS = ('name', 'id', 'last_func_name', 'last_func_mod', 'last_line_no', 'ttot', 'sched_count', 'last_func_full_name')
            
class YStats:
    """
    Main Stats class where we collect the information from _yappi and apply the user filters.
    """
    def __init__(self, enum_func=None):
        self._stats = []
        if enum_func:
            enum_func(self.enumerator)
        
    def sort(self, sort_type, sort_order):
        self._stats.sort(key=lambda stat: stat[sort_type], reverse=(sort_order==SORTORDER_DESC))
        
    def limit(self, limit):
        if limit != SHOW_ALL:
            self._stats = self._stats[:limit]

    def enumerator(self, stat_entry):
        pass

    def __iter__(self):
        for stat in self._stats:
            yield stat

    def __repr__(self):
        return str(self._stats)
        
    def __len__(self):
        return len(self._stats)
        
    def __getitem__(self, item):
        return self._stats[item]
        
    
class YFuncStats(YStats):

    _idx_max = 0
    
    def enumerator(self, stat_entry):
        tavg = stat_entry[4]/stat_entry[3]
        full_name = "%s:%s:%d" % (stat_entry[1], stat_entry[0], stat_entry[2])
        fstat = YFuncStat(stat_entry + (tavg,full_name))
        
        if os.path.basename(fstat.module) != "%s.py" % __name__: # do not show profile stats of yappi itself.
            self._stats.append(fstat)
            # hold the max idx number for merging new entries
            if self._idx_max < fstat.index:
                self._idx_max = fstat.index
            
    def add(self, path):
        def get_stat_by_full_name(stats, full_name):
            for stat in stats:
                if stat.full_name == full_name:
                    return stat
            return None
            
        def get_stat_by_index(stats, index):
            for stat in stats:
                if stat.index == index:
                    return stat
            return None
        
        of = open(path, "rb")
        saved_stats = pickle.load(of)
        of.close()
        
        # add 'not present' previous entries
        for saved_stat in saved_stats:
            if saved_stat not in self._stats:
                self._idx_max += 1
                saved_stat.index = self._idx_max
                self._stats.append(saved_stat)
            else:
                cur_stat = get_stat_by_full_name(self._stats, saved_stat.full_name)
                cur_stat.ncall += saved_stat.ncall
                cur_stat.ttot += saved_stat.ttot
                cur_stat.tsub += saved_stat.tsub
                cur_stat.tavg += saved_stat.tavg
                
        # fix the children indexes
        for saved_stat in saved_stats:
            for i in range(len(saved_stat.children)):
                child_stat = get_stat_by_index(saved_stats, saved_stat.children[i][0])
                if child_stat:
                    # we have merged the results in the loop above, so if a saved stat exists it shall
                    # also exist in the current stats
                    child_stat_in_current = get_stat_by_full_name(self._stats, child_stat.full_name)
                    saved_stat.children[i] = (child_stat_in_current.index, saved_stat.children[i][1],
                                                saved_stat.children[i][2])
                    saved_stat_in_current = get_stat_by_full_name(self._stats, saved_stat.full_name)    
                    cur_child_indexes = [x[0] for x in saved_stat_in_current.children]
                    # TODO: update children
                else:
                    # sometimes even the profile results does not contain the result because of filtering 
                    # or timing(call_leave called but call_enter is not)
                    del saved_stat.children[i]
            
    def save(self, path):
        of = open(path, "wb")
        pickle.dump(self._stats, of)
        of.close()
       
class YThreadStats(YStats):
    def enumerator(self, stat_entry):
        last_func_full_name = "%s:%s:%d" % (stat_entry[3], stat_entry[2], stat_entry[4])
        tstat = YThreadStat(stat_entry + (last_func_full_name, ))
        self._stats.append(tstat)

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

def start(builtins=False):
    """
    Start profiler.
    """
    threading.setprofile(__callback)
    _yappi.start(builtins)


def get_func_stats(sort_type=SORTTYPE_NCALL, sort_order=SORTORDER_DESC, limit=SHOW_ALL):
    """
    Gets the function profiler results with given filters and returns an iterable.
    """
    validate_func_sorttype(sort_type)
    validate_sortorder(sort_order)
    
    stats = YFuncStats(enum_func=enum_func_stats)
    stats.sort(sort_type, sort_order)
    stats.limit(limit)
    return stats

def get_thread_stats(sort_type=SORTTYPE_THREAD_NAME, sort_order=SORTORDER_DESC, limit=SHOW_ALL):
    """
    Gets the thread profiler results with given filters and returns an iterable.
    """
    validate_thread_sorttype(sort_type)
    validate_sortorder(sort_order)
    
    stats = YThreadStats(enum_func=enum_thread_stats)
    stats.sort(sort_type, sort_order)
    stats.limit(limit)
    return stats

def stop():
    """
    Stop profiler.
    """
    threading.setprofile(None)
    _yappi.stop()

def enum_func_stats(fenum):
    """
    Enumerates function profiler results and calls fenum for each line.
    """
    _yappi.enum_func_stats(fenum)

def enum_thread_stats(tenum):
    """
    Enumerates thread profiler results and calls fenum for each line.
    """
    _yappi.enum_thread_stats(tenum)

def print_func_stats(out=sys.stdout, stats=None, sort_type=SORTTYPE_NCALL, sort_order=SORTORDER_DESC, limit=SHOW_ALL):
    """
    Prints all of the function profiler results to a given file. (stdout by default)
    """
    
    if stats is None:
        stats = get_func_stats(sort_type, sort_order, limit)
    else:
        validate_func_sorttype(sort_type)
        validate_sortorder(sort_order)
        stats.sort(sort_type, sort_order)
        stats.limit(limit)

    FUNC_NAME_LEN = 38
    CALLCOUNT_LEN = 9
    
    out.write(CRLF)
    out.write("name                                    #n         tsub      ttot      tavg")
    out.write(CRLF)
    for stat in stats:
        out.write(StatString(stat.full_name).ltrim(FUNC_NAME_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString(stat.ncall).rtrim(CALLCOUNT_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString("%0.6f" % stat.tsub).rtrim(TIME_COLUMN_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString("%0.6f" % stat.ttot).rtrim(TIME_COLUMN_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString("%0.6f" % stat.tavg).rtrim(TIME_COLUMN_LEN))
        out.write(CRLF)
     

def print_thread_stats(out=sys.stdout, sort_type=SORTTYPE_NAME, sort_order=SORTORDER_DESC, limit=SHOW_ALL):
    """
    Prints all of the thread profiler results to a given file. (stdout by default)
    """
    stats = get_thread_stats(sort_type, sort_order, limit)

    THREAD_FUNC_NAME_LEN = 25
    THREAD_NAME_LEN = 13
    THREAD_ID_LEN = 15
    THREAD_SCHED_CNT_LEN = 10

    out.write(CRLF)
    out.write("name           tid              fname                      ttot      scnt")
    out.write(CRLF)
    for stat in stats:
        out.write(StatString(stat.name).ltrim(THREAD_NAME_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString(stat.id).rtrim(THREAD_ID_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString(stat.last_func_full_name).ltrim(THREAD_FUNC_NAME_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString("%0.6f" % stat.ttot).rtrim(TIME_COLUMN_LEN))
        out.write(" " * COLUMN_GAP)
        out.write(StatString(stat.sched_count).rtrim(THREAD_SCHED_CNT_LEN))
        out.write(CRLF)

def write_callgrind_stats(out=sys.stdout):
    """
    Writes all the function stats in a callgrind-style format to the given
    file. (stdout by default)
    """
    stats = get_func_stats()

    header = """version: 1
creator: %s
pid: %d
cmd:  %s
part: 1

events: Ticks
""" % ('yappi', os.getpid(), ' '.join(sys.argv))

    lines = [header]

    # add function definitions
    file_ids = ['']
    func_ids = ['']
    for func_stat in stats:
        file_ids += [ 'fl=(%d) %s' % (func_stat.index, func_stat.module) ]
        func_ids += [ 'fn=(%d) %s' % (func_stat.index, func_stat.name) ]

    lines += file_ids + func_ids

    # add stats for each function we have a record of
    for func_stat in stats:
        func_stats = [ '',
                       'fl=(%d)' % func_stat.index,
                       'fn=(%d)' % func_stat.index ]
        func_stats += [ '%s %s' % (func_stat.lineno, int(func_stat.tsub * 1e6)) ]

        # children functions stats
        for idx, callcount, ttot in func_stat.children:
            func_stats += [ 'cfl=(%d)' % idx,
                            'cfn=(%d)' % idx,
                            'calls=%d 0' % callcount,
                            '0 %d' % int(ttot * 1e6)
                            ]

        lines += func_stats

    out.write('\n'.join(lines))


def clear_stats():
    """
    Clears all of the profile results.
    """
    _yappi.clear_stats()

def clock_type():
    """
    Returns the internal native(OS dependant) API used to retrieve per-thread cputime and
    its resolution.
    """
    return _yappi.clock_type()

def thread_times():
    """
    Returns the total CPU time of the calling thread as a float.(in secs) Precision is OS dependent.
    """
    return _yappi.thread_times()

def mem_usage():
    """
    Returns the memory usage of the profiler itself.
    """
    return _yappi.mem_usage()

def main():
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
        start(options.profile_builtins)
        if sys.version_info >= (3, 0):
            exec(compile(open(sys.argv[0]).read(), sys.argv[0], 'exec'),
               sys._getframe(1).f_globals, sys._getframe(1).f_locals)
        else:
            execfile(sys.argv[0], sys._getframe(1).f_globals, sys._getframe(1).f_locals)
        stop()
        # we will currently use default params for these
        print_func_stats()
        print_thread_stats()
    else:
        parser.print_usage()


if __name__ == "__main__":
    main()
