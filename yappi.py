"""
 yappi.py
 Yet Another Python Profiler

 Sumer Cip 2013
"""
import os
import sys
import _yappi
import pickle
import marshal
import threading
        
class YappiError(Exception): pass

__all__ = ['start', 'stop', 'get_func_stats', 'get_thread_stats', 'clear_stats', 'is_running',
           'get_clock_type', 'set_clock_type',  'get_mem_usage']
           
CRLF = '\n'
COLUMN_GAP = 2
TIME_COLUMN_LEN = 8 # 0.000000, 12345.98, precision is microsecs
YPICKLE_PROTOCOL = 2

SORT_TYPES_FUNCSTATS = {"name":0, "callcount":3, "totaltime":6, "subtime":7, "avgtime":10,
                        "ncall":3, "ttot":6, "tsub":7, "tavg":10}
SORT_TYPES_CHILDFUNCSTATS = {"name":10, "callcount":1, "totaltime":3, "subtime":4, "avgtime":5,
                        "ncall":1, "ttot":3, "tsub":4, "tavg":5}
SORT_TYPES_THREADSTATS = {"name":0, "id":1, "totaltime":2, "schedcount":3,
                          "ttot":2, "scnt":3}
SORT_ORDERS = {"ascending":0, "asc":0, "descending":1, "desc":1}
DEFAULT_SORT_TYPE = "totaltime"
DEFAULT_SORT_ORDER = "desc"

CLOCK_TYPES = {"WALL":0, "CPU":1}

def _validate_sorttype(sort_type, list):
    sort_type = sort_type.lower()
    if sort_type not in list:
        raise YappiError("Invalid SortType parameter.[%s]" % (sort_type))
    return sort_type
       
def _validate_sortorder(sort_order):
    sort_order = sort_order.lower()
    if sort_order not in SORT_ORDERS:
        raise YappiError("Invalid SortOrder parameter.[%s]" % (sort_order))
    return sort_order
        
"""
 _callback will only be called once per-thread. _yappi will detect
 the new thread and changes the profilefunc param of the ThreadState
 structure. This is an internal function please don't mess with it.
"""
def _callback(frame, event, arg):
    _yappi._profile_event(frame, event, arg)
    return _callback
    
"""
function to prettify time columns in stats.
"""
def _fft(x):
    _rprecision = 6
    while(_rprecision > 0):
        _fmt = "%0." + "%d" % (_rprecision) + "f"
        s = _fmt % (x)
        if len(s) <= TIME_COLUMN_LEN:
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
convert the information to that.       

PSTAT only expects to have the above dict to be saved.
"""
def convert2pstats(stats):
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
    _callers = {}
    for fs in stats:
        if not fs in _callers:
            _callers[fs] = {}
            
        for ct in fs.children:
            if not ct in _callers:
                _callers[ct] = {}
            _callers[ct][pstat_id(fs)] = (ct.ncall, ct.nactualcall, ct.tsub ,ct.ttot)
    
    # populate the pstat dict.
    for fs in stats:
        _pdict[pstat_id(fs)] = (fs.ncall, fs.nactualcall, fs.tsub, fs.ttot, _callers[fs], )        
     
    return pstats.Stats(_PStatHolder(_pdict))
    
    
class StatString(object):
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
            
    def __setattr__(self, name, value):
        if name in self._KEYS:
            self[self._KEYS.index(name)] = value
        super(YStat, self).__setattr__(name, value)
    
class YFuncStat(YStat):
    """
    Class holding information for function stats.
    """
    _KEYS = ('name', 'module', 'lineno', 'ncall', 'nactualcall', 'builtin', 'ttot', 'tsub', 'index', 
        'children', 'tavg', 'full_name')
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.full_name == other.full_name
        
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
        return self.index
                   
    def is_recursive(self):
        # we have a known bug where call_leave not called for some thread functions(run() especially)
        # in that case ncalls will be updated in call_enter, however nactualcall will not. This is for
        # checking that case.
        if self.nactualcall == 0:
            return False
        return self.ncall != self.nactualcall

    def strip_dirs(self):
        self.full_name = _func_fullname(self.builtin, os.path.basename(self.module), 
            self.lineno, self.name)
        return self    
        
class YChildFuncStat(YFuncStat):
    """
    Class holding information for children function stats.
    """
    _KEYS = ('index', 'ncall', 'nactualcall', 'ttot', 'tsub', 'tavg', 'builtin', 'full_name',
        'module', 'lineno', 'name')
    
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
    _KEYS = ('name', 'id', 'ttot','sched_count',)
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.id == other.id

class YStats(object):
    """
    Main Stats class where we collect the information from _yappi and apply the user filters.
    """
    def __init__(self):
        self._stats = []
        self._clock_type = None
        
    def get(self):
        self._clock_type = _yappi.get_clock_type()["type"]
        return self.sort(DEFAULT_SORT_TYPE, DEFAULT_SORT_ORDER)
        
    def sort(self, sort_type, sort_order):
        self._stats.sort(key=lambda stat: stat[sort_type], reverse=(sort_order==SORT_ORDERS["desc"]))
        return self
        
    def clear(self):
        self._stats = []
    
    def empty(self):
        return (len(self._stats) == 0)
                
    def __iter__(self):
        for stat in self._stats:
            yield stat

    def __repr__(self):
        return str(self._stats)
        
    def __len__(self):
        return len(self._stats)
        
    def __getitem__(self, key):
        try:
            return self._stats[key]
        except IndexError:
            return None
    
    def append(self, item):
        # sometimes, we may have Stat object that seems to be unique, however
        # it may already be in the list.
        try:
            idx = self._stats.index(item)
            citem = self._stats[idx]
        except ValueError:
            self._stats.append(item)
            return
        citem += item
    
    def _debug_check_sanity(self):
        """
        Check for basic sanity errors in stats. e.g: Check for duplicate stats.
        """
        for x in self:
            if self._stats.count(x) > 1:
                return False
        return True
            
class YChildFuncStats(YStats):
    def __getitem__(self, key):        
        if isinstance(key, int):
            for item in self:
                if item.index == key:
                    return item
        elif isinstance(key, str):
            for item in self:
                if item.full_name == key:
                    return item
        elif isinstance(key, YFuncStat) or isinstance(key, YChildFuncStat):
            for item in self:
                if item.index == key.index:
                    return item
                    
        return super(YChildFuncStats, self).__getitem__(key)
        
    def sort(self, sort_type, sort_order="desc"):
        sort_type = _validate_sorttype(sort_type, SORT_TYPES_CHILDFUNCSTATS)
        sort_order = _validate_sortorder(sort_order)
        
        return super(YChildFuncStats, self).sort(SORT_TYPES_CHILDFUNCSTATS[sort_type], SORT_ORDERS[sort_order])
    
    def print_all(self, out=sys.stdout):
        """
        Prints all of the child function profiler results to a given file. (stdout by default)
        """
        if self.empty():
            return
        
        FUNC_NAME_LEN = 38
        CALLCOUNT_LEN = 9        
        out.write(CRLF)
        out.write("name                                    #n         tsub      ttot      tavg")
        out.write(CRLF)
        for stat in self:
            out.write(StatString(stat.full_name).ltrim(FUNC_NAME_LEN))
            out.write(" " * COLUMN_GAP)
            
            # the function is recursive?
            if stat.is_recursive():
                out.write(StatString("%d/%d" % (stat.ncall, stat.nactualcall)).rtrim(CALLCOUNT_LEN))
            else:
                out.write(StatString(stat.ncall).rtrim(CALLCOUNT_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.tsub)).rtrim(TIME_COLUMN_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.ttot)).rtrim(TIME_COLUMN_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.tavg)).rtrim(TIME_COLUMN_LEN))
            out.write(CRLF)
    
    def strip_dirs(self):
        for stat in self:
            stat.strip_dirs()
        return self
    
class YFuncStats(YStats):

    _idx_max = 0
    _sort_type = None
    _sort_order = None
    _SUPPORTED_LOAD_FORMATS = ['YSTAT']
    _SUPPORTED_SAVE_FORMATS = ['YSTAT', 'CALLGRIND', 'PSTAT']
    
    def __init__(self, files=[]):
        super(YFuncStats, self).__init__()
        self.add(files)
        
    def __getitem__(self, key):
        if isinstance(key, int):
            for item in self:
                if item.index == key:
                    return item
        elif isinstance(key, str):
            for item in self:
                if item.full_name == key:
                    return item
                    
        return super(YFuncStats, self).__getitem__(key)
        
    def strip_dirs(self):
        for stat in self:
            stat.strip_dirs()
            stat.children.strip_dirs()
        return self
        
    def get(self):        
        _yappi._pause()
        self.clear()
        try:        
            _yappi.enum_func_stats(self._enumerator)
            
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
        
        # builtin function?
        full_name = _func_fullname(bool(stat_entry[5]), stat_entry[1], stat_entry[2], stat_entry[0])                    
        tavg = stat_entry[6] / stat_entry[3]
        fstat = YFuncStat(stat_entry + (tavg, full_name))
        
        # do not show profile stats of yappi itself.
        if os.path.basename(fstat.module) == "yappi.py" or fstat.module == "_yappi":
            return
            
        fstat.builtin = bool(fstat.builtin)                
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
        file = open(path, "wb")
        try:
            pickle.dump((self._stats, self._clock_type), file, YPICKLE_PROTOCOL)
        finally:
            file.close()
            
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

        # add function definitions
        file_ids = ['']
        func_ids = ['']
        for func_stat in self:
            file_ids += [ 'fl=(%d) %s' % (func_stat.index, func_stat.module) ]
            func_ids += [ 'fn=(%d) %s %s:%s' % (func_stat.index, func_stat.name, func_stat.module, func_stat.lineno) ]

        lines += file_ids + func_ids

        # add stats for each function we have a record of
        for func_stat in self:
            func_stats = [ '',
                           'fl=(%d)' % func_stat.index,
                           'fn=(%d)' % func_stat.index]
            func_stats += [ '%s %s' % (func_stat.lineno, int(func_stat.tsub * 1e6)) ]

            # children functions stats
            for child in func_stat.children:
                func_stats += [ 'cfl=(%d)' % child.index,
                                'cfn=(%d)' % child.index,
                                'calls=%d 0' % child.ncall,
                                '0 %d' % int(child.ttot * 1e6)
                                ]
            lines += func_stats
            
        file = open(path, "w")
        try:
            file.write('\n'.join(lines))                
        finally:
            file.close()
            
    def add(self, files, type="ystat"):    
        type = type.upper()
        if type not in self._SUPPORTED_LOAD_FORMATS:
            raise NotImplementedError('Loading from (%s) format is not possible currently.')
        if isinstance(files, str):
            files = [files, ]
        for fd in files:
            f = open(fd, "rb")
            try:
                add_func = getattr(self, "_add_from_%s" % (type))
                add_func(file=f)
            finally:
                f.close()
            
        return self.sort(DEFAULT_SORT_TYPE, DEFAULT_SORT_ORDER)
            
    def save(self, path, type="ystat"):
        type = type.upper()
        if type not in self._SUPPORTED_SAVE_FORMATS:
            raise NotImplementedError('Saving in "%s" format is not possible currently.' % (type))
                    
        save_func = getattr(self, "_save_as_%s" % (type))
        save_func(path=path)
        
    def print_all(self, out=sys.stdout):
        """
        Prints all of the function profiler results to a given file. (stdout by default)
        """
        if self.empty():
            return
        
        FUNC_NAME_LEN = 38
        CALLCOUNT_LEN = 9
        out.write(CRLF)
        out.write("Clock type: %s" % (self._clock_type))
        out.write(CRLF)
        out.write("Ordered by: %s, %s" % (self._sort_type, self._sort_order))
        out.write(CRLF)
        out.write(CRLF)
        out.write("name                                    #n         tsub      ttot      tavg")
        out.write(CRLF)
        for stat in self:
            out.write(StatString(stat.full_name).ltrim(FUNC_NAME_LEN))
            out.write(" " * COLUMN_GAP)
            
            # the function is recursive?
            if stat.is_recursive():
                out.write(StatString("%d/%d" % (stat.ncall, stat.nactualcall)).rtrim(CALLCOUNT_LEN))
            else:
                out.write(StatString(stat.ncall).rtrim(CALLCOUNT_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.tsub)).rtrim(TIME_COLUMN_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.ttot)).rtrim(TIME_COLUMN_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.tavg)).rtrim(TIME_COLUMN_LEN))
            out.write(CRLF)
            
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
            console.write(CRLF)
            console.write("full_name: %s" % stat.full_name)
            console.write(CRLF)
            console.write("ncall: %d/%d" % (stat.ncall, stat.nactualcall))
            console.write(CRLF)
            console.write("ttot: %s" % _fft(stat.ttot))
            console.write(CRLF)
            console.write("tsub: %s" % _fft(stat.tsub))
            console.write(CRLF)
            console.write("children: ")
            console.write(CRLF)
            for child_stat in stat.children:
                console.write(CRLF)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("index: %d" % child_stat.index)
                console.write(CRLF)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("child_full_name: %s" % child_stat.full_name)
                console.write(CRLF)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("ncall: %d/%d" % (child_stat.ncall, child_stat.nactualcall))
                console.write(CRLF)
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("ttot: %s" % _fft(child_stat.ttot))
                console.write(CRLF)      
                console.write(" " * CHILD_STATS_LEFT_MARGIN)
                console.write("tsub: %s" % _fft(child_stat.tsub))
                console.write(CRLF) 
            console.write(CRLF)
         
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
        
    def print_all(self, out=sys.stdout):
        """
        Prints all of the thread profiler results to a given file. (stdout by default)
        """
        THREAD_FUNC_NAME_LEN = 25
        THREAD_NAME_LEN = 13
        THREAD_ID_LEN = 15
        THREAD_SCHED_CNT_LEN = 10

        out.write(CRLF)
        out.write("name           tid              ttot      scnt")
        out.write(CRLF)
        for stat in self:
            out.write(StatString(stat.name).ltrim(THREAD_NAME_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(stat.id).rtrim(THREAD_ID_LEN))            
            out.write(" " * COLUMN_GAP)
            out.write(StatString(_fft(stat.ttot)).rtrim(TIME_COLUMN_LEN))
            out.write(" " * COLUMN_GAP)
            out.write(StatString(stat.sched_count).rtrim(THREAD_SCHED_CNT_LEN))
            out.write(CRLF)
            
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
        threading.setprofile(_callback)
    _yappi.start(builtins, profile_threads)

def get_func_stats():
    """
    Gets the function profiler results with given filters and returns an iterable.
    """
    # multiple invocation pause/resume is allowed. This is needed because
    # not only get() is executed here.
    _yappi._pause()
    try:
        stats = YFuncStats().get()
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

def clear_stats():
    """
    Clears all of the profile results.
    """
    _yappi._pause()
    try:
        _yappi.clear_stats()
    finally:
        _yappi._resume()
    
def get_clock_type():
    """
    Returns the OS api used for timing plus the precision and the clock type information in a dict.
    """
    return _yappi.get_clock_type()
    
def set_clock_type(type):
    """
    Sets the internal clock type for timing. Profiler shall not have any previous stats.
    Otherwise an exception is thrown.
    """
    type = type.upper()
    if type not in CLOCK_TYPES:
        raise YappiError("Invalid clock type:%s" % (type))
        
    _yappi.set_clock_type(CLOCK_TYPES[type])

def get_mem_usage():
    """
    Returns the internal memory usage of the profiler itself.
    """
    return _yappi.get_mem_usage()
 
def main():
    from optparse import OptionParser
    usage = "yappi.py [-b] [-s] [scriptfile] args ..."
    parser = OptionParser(usage=usage)
    parser.allow_interspersed_args = False
    parser.add_option("-b", "--builtins",
                  action="store_true", dest="profile_builtins", default=False,
                  help="Profiles builtin functions when set. [default: False]")
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
        start(options.profile_builtins, not options.profile_single_thread)
        if sys.version_info >= (3, 0):
            exec(compile(open(sys.argv[0]).read(), sys.argv[0], 'exec'),
               sys._getframe(1).f_globals, sys._getframe(1).f_locals)
        else:
            execfile(sys.argv[0], sys._getframe(1).f_globals, sys._getframe(1).f_locals)
        stop()
        # we will currently use default params for these
        get_func_stats().print_all()
        get_thread_stats().print_all()
    else:
        parser.print_usage()

if __name__ == "__main__":
    main()
