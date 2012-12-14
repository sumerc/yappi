'''
 yappi.py
 Yet Another Python Profiler

 Sumer Cip 2012
'''
import os
import sys
import threading
import _yappi

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

class YStatDict(dict):
    """
    Class to hold a profile result line in a dict object, which all items can also be accessed as
    instance attributes where their attribute name is the given key. Mimicked NamedTuples.
    """
    def __init__(self, keys, values):
        super(YStatDict, self).__init__()
        assert len(keys) == len(values)
        for i in range(len(keys)):
            setattr(self, keys[i], values[i])
            self[i] = values[i]

    def __repr__(self):
        return str(self.__dict__)

class YStats:
    """
    Main Stats class where we collect the information from _yappi and apply the user filters.
    """
    def __init__(self, sort_type, sort_order, limit, enum_func):
        self._stats = []
        enum_func(self.enumerator)
        self.sort(sort_type, sort_order)
        self.limit(limit)

    def sort(self, sort_type, sort_order):
        self._stats.sort(key=lambda stat: stat[sort_type],
            reverse=(sort_order==SORTORDER_DESC))

    def limit(self, limit):
        if limit != SHOW_ALL:
            self._stats = self._stats[:limit]

    def enumerator(self, stat_entry):
        pass

    def __iter__(self):
        for stat in self._stats:
            yield stat

    def __getitem__(self, item):
        return self._stats[item]

    def __repr__(self):
        return str(self._stats)

class YFuncStats(YStats):
    def enumerator(self, stat_entry):
        tavg = stat_entry[4]/stat_entry[3]
        fstat = YStatDict(('name', 'module', 'lineno', 'ncall', 'ttot', 'tsub', 'index', 'children', 'tavg'), stat_entry+(tavg,))
        fstat.full_name = "%s:%s:%d" % (fstat.module, fstat.name, fstat.lineno)
        self._stats.append(fstat)

class YThreadStats(YStats):
    def enumerator(self, stat_entry):
        tstat = YStatDict(('name', 'id', 'last_func_name', 'last_func_mod', 'last_line_no', 'ttot', 'sched_count'), stat_entry)
        tstat.last_func_full_name = "%s:%s:%d" % (tstat.last_func_mod, tstat.last_func_name, tstat.last_line_no)
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
    stats = YFuncStats(sort_type, sort_order, limit, enum_func_stats)
    return stats

def get_thread_stats(sort_type=SORTTYPE_THREAD_NAME, sort_order=SORTORDER_DESC, limit=SHOW_ALL):
    """
    Gets the thread profiler results with given filters and returns an iterable.
    """
    stats = YThreadStats(sort_type, sort_order, limit, enum_thread_stats)
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

def print_func_stats(out=sys.stdout, sort_type=SORTTYPE_NCALL, sort_order=SORTORDER_DESC, limit=SHOW_ALL):
    """
    Prints all of the function profiler results to a given file. (stdout by default)
    """
    stats = get_func_stats(sort_type, sort_order, limit)

    FUNC_NAME_LEN = 38
    CALLCOUNT_LEN = 9

    out.write(CRLF)
    out.write("name                                    #n            tsub      ttot      tavg")
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

    lines = [ header ]

    # add function definitions
    idxmap = {}
    file_ids = ['']
    func_ids = ['']
    for idx, funcstat in enumerate(stats):
        idxmap[funcstat.index] = idx
        file_ids += [ 'fl=(%d) %s' % (idx, funcstat.module) ]
        func_ids += [ 'fn=(%d) %s' % (idx, funcstat.name) ]

    lines += file_ids + func_ids

    # add stats for each function we have a record of
    for idx, funcstat in enumerate(stats):
        func_stats = [ '',
                       'fl=(%d)' % idx,
                       'fn=(%d)' % idx ]
        func_stats += [ '%s %s' % (funcstat.lineno, int(funcstat.tsub * 1e6)) ]

        # children functions stats
        for idx, callcount, tsub in funcstat.children:
            if idx not in idxmap:
                continue
            func_stats += [ 'cfl=(%d)' % idxmap[idx],
                            'cfn=(%d)' % idxmap[idx],
                            'calls=%d 0' % callcount,
                            '0 %d' % int(tsub * 1e6)
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
