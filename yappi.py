"""
 yappi.py
 Yet Another Python Profiler

 Sumer Cip 2014
"""
import itertools
import os
import sys
import _yappi
import pickle
import threading
try:
    from thread import get_ident        # Python 2
except ImportError:
    from threading import get_ident     # Python 3

from collections import defaultdict
from contextlib import contextmanager

class YappiError(Exception): pass

__all__ = ['start', 'stop', 'get_func_stats', 'get_thread_stats', 'clear_stats', 'is_running',
           'get_clock_time', 'get_clock_type', 'set_clock_type', 'get_clock_info', 'get_mem_usage']

LINESEP = os.linesep
COLUMN_GAP = 2
YPICKLE_PROTOCOL = 2

COLUMNS_FUNCSTATS = ["name", "ncall", "ttot", "tsub", "tavg"]
COLUMNS_THREADSTATS = ["name", "id", "tid", "ttot", "scnt"]
SORT_TYPES_FUNCSTATS = {"name":0, "callcount":3, "totaltime":6, "subtime":7, "avgtime":10,
                        "ncall":3, "ttot":6, "tsub":7, "tavg":10}
SORT_TYPES_CHILDFUNCSTATS = {"name":10, "callcount":1, "totaltime":3, "subtime":4, "avgtime":5,
                        "ncall":1, "ttot":3, "tsub":4, "tavg":5}
SORT_TYPES_THREADSTATS = {"name":0, "id":1, "tid":2, "totaltime":3, "schedcount":4,
                          "ttot":3, "scnt":4}
SORT_ORDERS = {"ascending":0, "asc":0, "descending":1, "desc":1}
DEFAULT_SORT_TYPE = "totaltime"
DEFAULT_SORT_ORDER = "desc"

CLOCK_TYPES = {"WALL":0, "CPU":1}

def _validate_sorttype(sort_type, list):
    sort_type = sort_type.lower()
    if sort_type not in list:
        raise YappiError("Invalid SortType parameter: '%s'" % (sort_type))
    return sort_type

def _validate_sortorder(sort_order):
    sort_order = sort_order.lower()
    if sort_order not in SORT_ORDERS:
        raise YappiError("Invalid SortOrder parameter: '%s'" % (sort_order))
    return sort_order
    
def _validate_columns(name, list):
    name = name.lower()
    if name not in list:
        raise YappiError("Invalid Column name: '%s'" % (name))


def _ctx_name_callback():
    """
    We don't use threading.current_thread() becuase it will deadlock if
    called when profiling threading._active_limbo_lock.acquire().
    See: #Issue48.
    """
    try:
        current_thread = threading._active[get_ident()]
        return current_thread.__class__.__name__
    except KeyError: 
        # Threads may not be registered yet in first few profile callbacks.
        return None

def _profile_thread_callback(frame, event, arg):
    """
    _profile_thread_callback will only be called once per-thread. _yappi will detect
    the new thread and changes the profilefunc param of the ThreadState
    structure. This is an internal function please don't mess with it.
    """
    _yappi._profile_event(frame, event, arg)
    
def _fft(x, COL_SIZE=8):
    """
    function to prettify time columns in stats.
    """
    _rprecision = 6
    while(_rprecision > 0):
        _fmt = "%0." + "%d" % (_rprecision) + "f"
        s = _fmt % (x)
        if len(s) <= COL_SIZE:
            break
        _rprecision -= 1
    return s

def _func_fullname(builtin, module, lineno, name):
    if builtin:
        return "%s.%s" % (module, name)
    else:
        return "%s:%d %s" % (module, lineno, name)

"""
Converts our internal yappi's YFuncStats (YSTAT type) to PSTAT. So there are
some differences between the statistics parameters. The PSTAT format is as following:

PSTAT expects a dict. entry as following:

stats[("mod_name", line_no, "func_name")] = \
    ( total_call_count, actual_call_count, total_time, cumulative_time,
    {
        ("mod_name", line_no, "func_name") :
        (total_call_count, --> total count caller called the callee
        actual_call_count, --> total count caller called the callee - (recursive calls)
        total_time,        --> total time caller spent _only_ for this function (not further subcalls)
        cumulative_time)   --> total time caller spent for this function
    } --> callers dict
    )

Note that in PSTAT the total time spent in the function is called as cumulative_time and
the time spent _only_ in the function as total_time. From Yappi's perspective, this means:

total_time (inline time) = tsub
cumulative_time (total time) = ttot

Other than that we hold called functions in a profile entry as named 'children'. On the
other hand, PSTAT expects to have a dict of callers of the function. So we also need to
convert children to callers dict.
From Python Docs:
'''
With cProfile, each caller is preceded by three numbers:
the number of times this specific call was made, and the total
and cumulative times spent in the current function while it was
invoked by this specific caller.
'''
That means we only need to assign ChildFuncStat's ttot/tsub values to the caller
properly. Docs indicate that when b() is called by a() pstat holds the total time
of b() when called by a, just like yappi.

PSTAT only expects to have the above dict to be saved.
"""
def convert2pstats(stats):
    from collections import defaultdict
    """
    Converts the internal stat type of yappi(which is returned by a call to YFuncStats.get())
    as pstats object.
    """
    if not isinstance(stats, YFuncStats):
        raise YappiError("Source stats must be derived from YFuncStats.")

    import pstats
    class _PStatHolder:
        def __init__(self, d):
            self.stats = d
        def create_stats(self):
            pass
    def pstat_id(fs):
        return (fs.module, fs.lineno, fs.name)

    _pdict = {}

    # convert callees to callers
    _callers = defaultdict(dict)
    for fs in stats:
        for ct in fs.children:
            _callers[ct][pstat_id(fs)] = (ct.ncall, ct.nactualcall, ct.tsub ,ct.ttot)

    # populate the pstat dict.
    for fs in stats:
        _pdict[pstat_id(fs)] = (fs.ncall, fs.nactualcall, fs.tsub, fs.ttot, _callers[fs], )

    return pstats.Stats(_PStatHolder(_pdict))

def profile(clock_type="cpu", profile_builtins=False, return_callback=None):
    """
    A profile decorator that can be used to profile a single call.

    We need to clear_stats() on entry/exit of the function unfortunately.
    As yappi is a per-interpreter resource, we cannot simply resume profiling
    session upon exit of the function, that is because we _may_ simply change
    start() params which may differ from the paused session that may cause instable
    results. So, if you use a decorator, then global profiling may return bogus
    results or no results at all.
    """
    def _profile_dec(func):
        def wrapper(*args, **kwargs):
            if func._rec_level == 0:
                clear_stats()
                set_clock_type(clock_type)
                start(profile_builtins, profile_threads=False)
            func._rec_level += 1
            try:
                return func(*args, **kwargs)
            finally:
                func._rec_level -= 1
                # only show profile information when recursion level of the
                # function becomes 0. Otherwise, we are in the middle of a
                # recursive call tree and not finished yet.
                if func._rec_level == 0:
                    try:
                        stop()
                        if return_callback is None:
                            sys.stdout.write(LINESEP)
                            sys.stdout.write("Executed in %s %s clock seconds" %
                                (_fft(get_thread_stats()[0].ttot), clock_type.upper()))
                            sys.stdout.write(LINESEP)
                            get_func_stats().print_all()
                        else:
                            return_callback(func, get_func_stats())
                    finally:
                        clear_stats()
        func._rec_level = 0
        return wrapper
    return _profile_dec

class StatString(object):
    """
    Class to prettify/trim a profile result column.
    """
    _TRAIL_DOT = ".."
    _LEFT = 1
    _RIGHT = 2

    def __init__(self, s):
        self._s = str(s)

    def _trim(self, length, direction):
        if (len(self._s) > length):
            if direction == self._LEFT:
                self._s = self._s[-length:]
                return self._TRAIL_DOT + self._s[len(self._TRAIL_DOT):]
            elif direction == self._RIGHT:
                self._s = self._s[:length]
                return self._s[:-len(self._TRAIL_DOT)] + self._TRAIL_DOT
        return self._s + (" " * (length - len(self._s)))

    def ltrim(self, length):
        return self._trim(length, self._LEFT)

    def rtrim(self, length):
        return self._trim(length, self._RIGHT)

class YStat(dict):
    """
    Class to hold a profile result line in a dict object, which all items can also be accessed as
    instance attributes where their attribute name is the given key. Mimicked NamedTuples.
    """
    _KEYS = {}

    def __init__(self, values):
        super(YStat, self).__init__()

        for key,i in self._KEYS.items():
            setattr(self, key, values[i])

    def __setattr__(self, name, value):
        self[self._KEYS[name]] = value
        super(YStat, self).__setattr__(name, value)

class YFuncStat(YStat):
    """
    Class holding information for function stats.
    """
    _KEYS = {'name':0, 'module':1, 'lineno':2, 'ncall':3, 'nactualcall':4, 'builtin':5, 'ttot':6, 'tsub':7, 'index':8, 'children':9, 'ctx_id':10, 'tavg':11, 'full_name':12}

    def __eq__(self, other):
        if other is None:
            return False
        return self.full_name == other.full_name
    
    def __ne__(self, other):
        return not self == other

    def __add__(self, other):

        # do not merge if merging the same instance
        if self is other:
            return self

        self.ncall += other.ncall
        self.nactualcall += other.nactualcall
        self.ttot += other.ttot
        self.tsub += other.tsub
        self.tavg = self.ttot / self.ncall

        for other_child_stat in other.children:
            # all children point to a valid entry, and we shall have merged previous entries by here.
            self.children.append(other_child_stat)
        return self

    def __hash__(self):
        return hash(self.full_name)

    def is_recursive(self):
        # we have a known bug where call_leave not called for some thread functions(run() especially)
        # in that case ncalls will be updated in call_enter, however nactualcall will not. This is for
        # checking that case.
        if self.nactualcall == 0:
            return False
        return self.ncall != self.nactualcall

    def strip_dirs(self):
        self.module = os.path.basename(self.module)
        self.full_name = _func_fullname(self.builtin, self.module, self.lineno,
            self.name)
        return self

    def _print(self, out, columns):
        for x in sorted(columns.keys()):
            title, size = columns[x]
            if title == "name":
                out.write(StatString(self.full_name).ltrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "ncall":
                if self.is_recursive():
                    out.write(StatString("%d/%d" % (self.ncall,
                            self.nactualcall)).rtrim(size))
                else:
                    out.write(StatString(self.ncall).rtrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "tsub":
                out.write(StatString(_fft(self.tsub, size)).rtrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "ttot":
                out.write(StatString(_fft(self.ttot, size)).rtrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "tavg":
                out.write(StatString(_fft(self.tavg, size)).rtrim(size))
        out.write(LINESEP)

class YChildFuncStat(YFuncStat):
    """
    Class holding information for children function stats.
    """
    _KEYS = {'index':0, 'ncall':1, 'nactualcall':2, 'ttot':3, 'tsub':4, 'tavg':5, 'builtin':6, 'full_name':7, 'module':8, 'lineno':9, 'name':10}

    def __add__(self, other):
        if other is None:
            return self
        self.nactualcall += other.nactualcall
        self.ncall += other.ncall
        self.ttot += other.ttot
        self.tsub += other.tsub
        self.tavg = self.ttot / self.ncall
        return self

class YThreadStat(YStat):
    """
    Class holding information for thread stats.
    """
    _KEYS = {'name':0, 'id':1, 'tid':2, 'ttot':3,'sched_count':4,}

    def __eq__(self, other):
        if other is None:
            return False
        return self.id == other.id
    
    def __ne__(self, other):
        return not self == other
    
    def __hash__(self, *args, **kwargs):
        return hash(self.id)

    def _print(self, out, columns):
        for x in sorted(columns.keys()):
            title, size = columns[x]
            if title == "name":
                out.write(StatString(self.name).ltrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "id":
                out.write(StatString(self.id).rtrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "tid":
                out.write(StatString(self.tid).rtrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "ttot":
                out.write(StatString(_fft(self.ttot, size)).rtrim(size))
                out.write(" " * COLUMN_GAP)
            elif title == "scnt":
                out.write(StatString(self.sched_count).rtrim(size))
        out.write(LINESEP)

class YStats(object):
    """
    Main Stats class where we collect the information from _yappi and apply the user filters.
    """
    def __init__(self):
        self._clock_type = None
        self._as_dict = {}
        self._as_list = []

    def get(self):
        self._clock_type = _yappi.get_clock_type()
        self.sort(DEFAULT_SORT_TYPE, DEFAULT_SORT_ORDER)
        return self

    def sort(self, sort_type, sort_order):
        self._as_list.sort(key=lambda stat: stat[sort_type], 
            reverse=(sort_order==SORT_ORDERS["desc"]))
        return self

    def clear(self):
        del self._as_list[:]
        self._as_dict.clear()

    def empty(self):
        return (len(self._as_list) == 0)

    def __getitem__(self, key):
        try:
            return self._as_list[key]
        except IndexError:
            return None
        
    def count(self, item):
        return self._as_list.count(item)
    
    def __iter__(self):
        return iter(self._as_list)
    
    def __len__(self):
        return len(self._as_list)
    
    def pop(self):
        item = self._as_list.pop()
        del self._as_dict[item]
        return item

    def append(self, item):
        # increment/update the stat if we already have it
        
        existing = self._as_dict.get(item)
        if existing:
            existing += item
            return
        self._as_list.append(item)
        self._as_dict[item] = item

    def _print_header(self, out, columns):
        for x in sorted(columns.keys()):
            title, size = columns[x]
            if len(title) > size:
                raise YappiError("Column title exceeds available length[%s:%d]" % \
                    (title, size))
            out.write(title)
            out.write(" " * (COLUMN_GAP + size - len(title)))
        out.write(LINESEP)

    def _debug_check_sanity(self):
        """
        Check for basic sanity errors in stats. e.g: Check for duplicate stats.
        """
        for x in self:
            if self.count(x) > 1:
                return False
        return True
    

class YStatsIndexable(YStats):
    
    def __init__(self):
        super(YStatsIndexable, self).__init__()
        self._additional_indexing = {}
    
    def clear(self):
        super(YStatsIndexable, self).clear()
        self._additional_indexing.clear()
         
    def pop(self):
        item = super(YStatsIndexable, self).pop()
        self._additional_indexing.pop(item.index, None)
        self._additional_indexing.pop(item.full_name, None)
        return item
     
    def append(self, item):
        super(YStatsIndexable, self).append(item)
        # setdefault so that we don't replace them if they're already there.
        self._additional_indexing.setdefault(item.index, item)
        self._additional_indexing.setdefault(item.full_name, item)

    def __getitem__(self, key):
        if isinstance(key, int):
            # search by item.index
            return self._additional_indexing.get(key, None)
        elif isinstance(key, str):
            # search by item.full_name
            return self._additional_indexing.get(key, None)
        elif isinstance(key, YFuncStat) or isinstance(key, YChildFuncStat):
            return self._additional_indexing.get(key.index, None)

        return super(YStatsIndexable, self).__getitem__(key)

class YChildFuncStats(YStatsIndexable):

    def sort(self, sort_type, sort_order="desc"):
        sort_type = _validate_sorttype(sort_type, SORT_TYPES_CHILDFUNCSTATS)
        sort_order = _validate_sortorder(sort_order)

        return super(YChildFuncStats, self).sort(SORT_TYPES_CHILDFUNCSTATS[sort_type], SORT_ORDERS[sort_order])

    def print_all(self, out=sys.stdout, columns= {0:("name",36), 1:("ncall", 5), 
                    2:("tsub", 8), 3: ("ttot", 8), 4:("tavg",8)}):
        """
        Prints all of the child function profiler results to a given file. (stdout by default)
        """
        if self.empty() or len(columns) == 0:
            return

        for _, col in columns.items():
            _validate_columns(col[0], COLUMNS_FUNCSTATS)

        out.write(LINESEP)
        self._print_header(out, columns)
        for stat in self:
            stat._print(out, columns)

    def strip_dirs(self):
        for stat in self:
            stat.strip_dirs()
        return self
    

class YFuncStats(YStatsIndexable):

    _idx_max = 0
    _sort_type = None
    _sort_order = None
    _SUPPORTED_LOAD_FORMATS = ['YSTAT']
    _SUPPORTED_SAVE_FORMATS = ['YSTAT', 'CALLGRIND', 'PSTAT']

    def __init__(self, files=[]):
        super(YFuncStats, self).__init__()
        self.add(files)
        
    def strip_dirs(self):
        for stat in self:
            stat.strip_dirs()
            stat.children.strip_dirs()
        return self

    def get(self, filter=None):
        _yappi._pause()
        self.clear()
        try:
            self._filter = filter
            _yappi.enum_func_stats(self._enumerator)
            self._filter = None

            # convert the children info from tuple to YChildFuncStat
            for stat in self:

                _childs = YChildFuncStats()
                for child_tpl in stat.children:
                    rstat = self[child_tpl[0]]

                    # sometimes even the profile results does not contain the result because of filtering
                    # or timing(call_leave called but call_enter is not), with this we ensure that the children
                    # index always point to a valid stat.
                    if rstat is None:
                        continue

                    tavg = rstat.ttot / rstat.ncall
                    cfstat = YChildFuncStat(child_tpl+(tavg, rstat.builtin, rstat.full_name, rstat.module,
                        rstat.lineno, rstat.name,))
                    _childs.append(cfstat)
                stat.children = _childs
            result = super(YFuncStats, self).get()
        finally:
            _yappi._resume()
        return result

    def _enumerator(self, stat_entry):

        fname, fmodule, flineno, fncall, fnactualcall, fbuiltin, fttot, ftsub, \
            findex, fchildren, fctxid = stat_entry

        # builtin function?
        ffull_name = _func_fullname(bool(fbuiltin), fmodule, flineno, fname)
        ftavg = fttot / fncall
        fstat = YFuncStat(stat_entry + (ftavg, ffull_name))

        # do not show profile stats of yappi itself.
        if os.path.basename(fstat.module) == "yappi.py" or fstat.module == "_yappi":
            return

        fstat.builtin = bool(fstat.builtin)

        if self._filter:
            for k,v in self._filter.items():
                if getattr(fstat, k) != v:
                    return

        self.append(fstat)

        # hold the max idx number for merging new entries(for making the merging entries indexes unique)
        if self._idx_max < fstat.index:
            self._idx_max = fstat.index

    def _add_from_YSTAT(self, file):
        try:
            saved_stats, saved_clock_type = pickle.load(file)
        except:
            raise YappiError("Unable to load the saved profile information from %s." % (file.name))

        # check if we really have some stats to be merged?
        if not self.empty():
            if self._clock_type != saved_clock_type and self._clock_type is not None:
                raise YappiError("Clock type mismatch between current and saved profiler sessions.[%s,%s]" % \
                    (self._clock_type, saved_clock_type))

        self._clock_type = saved_clock_type

        # add 'not present' previous entries with unique indexes
        for saved_stat in saved_stats:
            if saved_stat not in self:
                self._idx_max += 1
                saved_stat.index = self._idx_max
                self.append(saved_stat)

        # fix children's index values
        for saved_stat in saved_stats:
            for saved_child_stat in saved_stat.children:
                # we know for sure child's index is pointing to a valid stat in saved_stats
                # so as saved_stat is already in sync. (in above loop), we can safely assume
                # that we shall point to a valid stat in current_stats with the child's full_name
                saved_child_stat.index = self[saved_child_stat.full_name].index

        # merge stats
        for saved_stat in saved_stats:
            saved_stat_in_curr = self[saved_stat.full_name]
            saved_stat_in_curr += saved_stat

    def _save_as_YSTAT(self, path):
        with open(path, "wb") as f:
            pickle.dump((self, self._clock_type), f, YPICKLE_PROTOCOL)

    def _save_as_PSTAT(self, path):
        """
        Save the profiling information as PSTAT.
        """
        _stats = convert2pstats(self)
        _stats.dump_stats(path)

    def _save_as_CALLGRIND(self, path):
        """
        Writes all the function stats in a callgrind-style format to the given
        file. (stdout by default)
        """
        header = """version: 1\ncreator: %s\npid: %d\ncmd:  %s\npart: 1\n\nevents: Ticks""" % \
            ('yappi', os.getpid(), ' '.join(sys.argv))

        lines = [header]

        # Each function has a distinct number even if its name already has a
        # number because kcachegrind merges functions with the same number.
        numbers_seq = itertools.count()
        func_defs = lambda: defaultdict(lambda: defaultdict(lambda: next(numbers_seq)))
        modules_seq = enumerate(iter(func_defs, None))
        modules = defaultdict(lambda: next(modules_seq))
        # modules = {'file.py': [module_index, {'func': {line: func_index}}]}
        fl = lambda x: modules[x.module][0]
        fn = lambda x: modules[x.module][1][x.name][x.lineno]

        # enumerate modules and functions
        for func_stat in self:
            fn(func_stat)
            for child in func_stat.children:
                fn(child)

        # add function definitions
        for module in sorted(modules):
            lines += ['', 'fl=(%d) %s' % (modules[module][0], module)]
            for func, defs in sorted(modules[module][1].items()):
                suffix = ''
                for line in sorted(defs):
                    if len(defs) > 1:  # disambiguate redefined functions
                        suffix = ' +%d' % line
                    lines += ['fn=(%d) %s%s' % (defs[line], func, suffix)]

        # add stats for each function we have a record of
        for func_stat in self:
            func_stats = [ '',
                           'fl=(%d)' % fl(func_stat),
                           'fn=(%d)' % fn(func_stat)]
            func_stats += [ '%s %s' % (func_stat.lineno, int(func_stat.tsub * 1e6)) ]

            # children functions stats
            for child in func_stat.children:
                func_stats += [ 'cfl=(%d)' % fl(child),
                                'cfn=(%d)' % fn(child),
                                'calls=%d 0' % child.ncall,
                                '0 %d' % int(child.ttot * 1e6)
                                ]
            lines += func_stats

        with open(path, "w") as f:
            f.write('\n'.join(lines))

    def add(self, files, type="ystat"):
        type = type.upper()
        if type not in self._SUPPORTED_LOAD_FORMATS:
            raise NotImplementedError('Loading from (%s) format is not possible currently.')
        if isinstance(files, str):
            files = [files, ]
        for fd in files:
            with open(fd, "rb") as f:
                add_func = getattr(self, "_add_from_%s" % (type))
                add_func(file=f)

        return self.sort(DEFAULT_SORT_TYPE, DEFAULT_SORT_ORDER)

    def save(self, path, type="ystat"):
        type = type.upper()
        if type not in self._SUPPORTED_SAVE_FORMATS:
            raise NotImplementedError('Saving in "%s" format is not possible currently.' % (type))

        save_func = getattr(self, "_save_as_%s" % (type))
        save_func(path=path)

    def print_all(self, out=sys.stdout, columns={0:("name",36), 1:("ncall", 5), 
                    2:("tsub", 8), 3:("ttot", 8), 4:("tavg",8)}):
        """
        Prints all of the function profiler results to a given file. (stdout by default)
        """
        if self.empty():
            return

        for _, col in columns.items():
            _validate_columns(col[0], COLUMNS_FUNCSTATS)

        out.write(LINESEP)
        out.write("Clock type: %s" % (self._clock_type.upper()))
        out.write(LINESEP)
        out.write("Ordered by: %s, %s" % (self._sort_type, self._sort_order))
        out.write(LINESEP)
        out.write(LINESEP)

        self._print_header(out, columns)
        for stat in self:
            stat._print(out, columns)

    def sort(self, sort_type, sort_order="desc"):
        sort_type = _validate_sorttype(sort_type, SORT_TYPES_FUNCSTATS)
        sort_order = _validate_sortorder(sort_order)

        self._sort_type = sort_type
        self._sort_order = sort_order

        return super(YFuncStats, self).sort(SORT_TYPES_FUNCSTATS[sort_type], SORT_ORDERS[sort_order])

    def debug_print(self):
        if self.empty():
            return

        console = sys.stdout
        CHILD_STATS_LEFT_MARGIN = 5
        for stat in self:
            console.write("index: %d" % stat.index)
            console.write(LINESEP)
            console.write("full_name: %s" % stat.full_name)
            console.write(LINESEP)
            console.write("ncall: %d/%d" % (stat.ncall, stat.nactualcall))
            console.write(LINESEP)
            console.write("ttot: %s" % _fft(stat.ttot))
            console.write(LINESEP)
            console.write("tsub: %s" % _fft(stat.tsub))
            console.write(LINESEP)
            console.write("children: ")
            console.write(LINESEP)
            for child_stat in stat.children:
                console.write(LINESEP)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("index: %d" % child_stat.index)
                console.write(LINESEP)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("child_full_name: %s" % child_stat.full_name)
                console.write(LINESEP)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("ncall: %d/%d" % (child_stat.ncall, child_stat.nactualcall))
                console.write(LINESEP)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("ttot: %s" % _fft(child_stat.ttot))
                console.write(LINESEP)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("tsub: %s" % _fft(child_stat.tsub))
                console.write(LINESEP)
            console.write(LINESEP)

class YThreadStats(YStats):

    def get(self):
        _yappi._pause()
        self.clear()
        try:
            _yappi.enum_thread_stats(self._enumerator)
            result = super(YThreadStats, self).get()
        finally:
            _yappi._resume()
        return result

    def _enumerator(self, stat_entry):
        tstat = YThreadStat(stat_entry)
        self.append(tstat)

    def sort(self, sort_type, sort_order="desc"):
        sort_type = _validate_sorttype(sort_type, SORT_TYPES_THREADSTATS)
        sort_order = _validate_sortorder(sort_order)

        return super(YThreadStats, self).sort(SORT_TYPES_THREADSTATS[sort_type], SORT_ORDERS[sort_order])

    def print_all(self, out=sys.stdout, columns={0:("name",13), 1:("id", 5), 
                2:("tid", 15), 3:("ttot", 8), 4:("scnt", 10)}):
        """
        Prints all of the thread profiler results to a given file. (stdout by default)
        """

        if self.empty():
            return
        
        for _, col in columns.items():
            _validate_columns(col[0], COLUMNS_THREADSTATS)

        out.write(LINESEP)
        self._print_header(out, columns)
        for stat in self:
            stat._print(out, columns)

    def strip_dirs(self):
        pass # do nothing

def is_running():
    """
    Returns true if the profiler is running, false otherwise.
    """
    return bool(_yappi.is_running())

def start(builtins=False, profile_threads=True):
    """
    Start profiler.
    """
    if profile_threads:
        threading.setprofile(_profile_thread_callback)
    _yappi.start(builtins, profile_threads)

def get_func_stats(filter=None):
    """
    Gets the function profiler results with given filters and returns an iterable.
    """
    # multiple invocation pause/resume is allowed. This is needed because
    # not only get() is executed here.
    _yappi._pause()
    try:
        stats = YFuncStats().get(filter=filter)
    finally:
        _yappi._resume()
    return stats

def get_thread_stats():
    """
    Gets the thread profiler results with given filters and returns an iterable.
    """
    _yappi._pause()
    try:
        stats = YThreadStats().get()
    finally:
        _yappi._resume()
    return stats

def stop():
    """
    Stop profiler.
    """
    _yappi.stop()
    threading.setprofile(None)

@contextmanager
def run(builtins=False, profile_threads=True):
    """
    Context manger for profiling block of code.

    Starts profiling before entering the context, and stop profilying when
    exiting from the context.

    Usage:

        with yappi.run():
            print("this call is profiled")

    Warning: don't use this recursively, the inner context will stop profiling
    when exited:

        with yappi.run():
            with yappi.run():
                print("this call will be profiled")
            print("this call will *not* be profiled")
    """
    start(builtins=builtins, profile_threads=profile_threads)
    try:
        yield
    finally:
        stop()

def clear_stats():
    """
    Clears all of the profile results.
    """
    _yappi._pause()
    try:
        _yappi.clear_stats()
    finally:
        _yappi._resume()

def get_clock_time():
    """
    Returns the current clock time with regard to current clock type.
    """
    return _yappi.get_clock_time()

def get_clock_type():
    """
    Returns the underlying clock type
    """
    return _yappi.get_clock_type()

def get_clock_info():
    """
    Returns a dict containing the OS API used for timing, the precision of the
    underlying clock.
    """
    return _yappi.get_clock_info()

def set_clock_type(type):
    """
    Sets the internal clock type for timing. Profiler shall not have any previous stats.
    Otherwise an exception is thrown.
    """
    type = type.upper()
    if type not in CLOCK_TYPES:
        raise YappiError("Invalid clock type:%s" % (type))

    _yappi.set_clock_type(CLOCK_TYPES[type])

def shift_context_time(context_id, amount):
    """
    Adjust a context's start time, and the time of all functions currently on
    the context's stack. 'amount' is in the same units as get_clock_type(). A
    negative 'amount' increases the 'ttot' statistic for this context and all
    functions on the stack, and a positive 'amount' decreases 'ttot'.
    """
    _yappi.shift_context_time(context_id, amount)

def get_mem_usage():
    """
    Returns the internal memory usage of the profiler itself.
    """
    return _yappi.get_mem_usage()

def set_context_id_callback(callback):
    """
    Use a number other than thread_id to determine the current context.

    The callback must take no arguments and return an integer. For example:

    >>> import greenlet, yappi
    >>> yappi.set_context_id_callback(lambda: id(greenlet.getcurrent()))
    """
    return _yappi.set_context_id_callback(callback)

def set_context_name_callback(callback):
    """
    Set the callback to retrieve current context's name.

    The callback must take no arguments and return a string. For example:

    >>> import greenlet, yappi
    >>> yappi.set_context_name_callback(
    ...     lambda: greenlet.getcurrent().__class__.__name__)

    If the callback cannot return the name at this time but may be able to
    return it later, it should return None.
    """
    if callback is None:
        return _yappi.set_context_name_callback(_ctx_name_callback)
    return _yappi.set_context_name_callback(callback)

# set _ctx_name_callback by default at import time. 
set_context_name_callback(None)

def main():
    from optparse import OptionParser
    usage = "%s [-b] [-c clock_type] [-o output_file] [-f output_format] [-s] [scriptfile] args ..." % os.path.basename(sys.argv[0])
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    parser.add_option("-c", "--clock-type", default="cpu",
                      choices=sorted(c.lower() for c in CLOCK_TYPES),
                      metavar="clock_type", help="Clock type to use during profiling"
                                "(\"cpu\" or \"wall\", default is \"cpu\").")
    parser.add_option("-b", "--builtins",
                  action="store_true", dest="profile_builtins", default=False,
                  help="Profiles builtin functions when set. [default: False]")
    parser.add_option("-o", "--output-file", metavar="output_file",
                  help="Write stats to output_file.")
    parser.add_option("-f", "--output-format", default="pstat",
                  choices=("pstat", "callgrind", "ystat"),
                  metavar="output_format", help="Write stats in the specified"
                  "format (\"pstat\", \"callgrind\" or \"ystat\", default is "
                  "\"pstat\").")
    parser.add_option("-s", "--single_thread",
                  action="store_true", dest="profile_single_thread", default=False,
                  help="Profiles only the thread that calls start(). [default: False]")
    if not sys.argv[1:]:
        parser.print_usage()
        sys.exit(2)

    (options, args) = parser.parse_args()
    sys.argv[:] = args

    if (len(sys.argv) > 0):
        sys.path.insert(0, os.path.dirname(sys.argv[0]))
        set_clock_type(options.clock_type)
        start(options.profile_builtins, not options.profile_single_thread)
        try:
            if sys.version_info >= (3, 0):
                exec(compile(open(sys.argv[0]).read(), sys.argv[0], 'exec'),
                   sys._getframe(1).f_globals, sys._getframe(1).f_locals)
            else:
                execfile(sys.argv[0], sys._getframe(1).f_globals, sys._getframe(1).f_locals)
        finally:
            stop()
            if options.output_file:
                stats = get_func_stats()
                stats.save(options.output_file, options.output_format)
            else:
                # we will currently use default params for these
                get_func_stats().print_all()
                get_thread_stats().print_all()
    else:
        parser.print_usage()

if __name__ == "__main__":
    main()
