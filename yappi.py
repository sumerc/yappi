'''

 yappi.py
 Yet Another Python Profiler

 Sumer Cip 2010

'''
import sys
import threading
import _yappi

__all__ = ['start', 'stop', 'enum_stats', 'print_stats', 'clear_stats']

SORTTYPE_NAME = _yappi.SORTTYPE_NAME
SORTTYPE_NCALL = _yappi.SORTTYPE_NCALL
SORTTYPE_TTOTAL = _yappi.SORTTYPE_TTOTAL
SORTTYPE_TSUB = _yappi.SORTTYPE_TSUB
SORTTYPE_TAVG = _yappi.SORTTYPE_TAVG
SORTORDER_ASCENDING = _yappi.SORTORDER_ASCENDING
SORTORDER_DESCENDING = _yappi.SORTORDER_DESCENDING
SHOW_ALL = _yappi.SHOW_ALL

'''
 __callback will only be called once per-thread. _yappi will detect
 the new thread and changes the profilefunc param of the ThreadState
 structure. This is an internal function please don't mess with it.
'''
def __callback(frame, event, arg):
    _yappi.profile_event(frame, event, arg)
    return __callback
'''
...
Args:
builtins: If set true, then builtin functions are profiled too.
timing_sample: will cause the profiler to do timing measuresements
               according to the value. Will increase profiler speed but
               decrease accuracy.
'''
def start(builtins = False):
    threading.setprofile(__callback)
    _yappi.start(builtins)

def stop():
    threading.setprofile(None)
    _yappi.stop()

def enum_stats(fenum):
    _yappi.enum_stats(fenum)

def get_stats(sorttype=_yappi.SORTTYPE_NCALL,
        sortorder=_yappi.SORTORDER_DESCENDING,
        limit=_yappi.SHOW_ALL):
    return _yappi.get_stats(sorttype, sortorder, limit)

def print_stats(sorttype=_yappi.SORTTYPE_NCALL,
        sortorder=_yappi.SORTORDER_DESCENDING,
        limit=_yappi.SHOW_ALL):
    li = get_stats(sorttype, sortorder, limit)
    for it in li: print(it)

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


