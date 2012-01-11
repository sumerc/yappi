import sys

def test_passed(msg):
    sys.stdout.write("[+]    TEST: %s passed.\r\n" % (msg))
    
def _run(func):
    import __main__
    globals = locals = __main__.__dict__
    if sys.hexversion > 0x03000000:
        exec(func, globals, locals) 
    else:   
        # todo: port python 2.x??
        pass
        
def func_stat_from_name(stats, fname):
    for stat in stats.func_stats:
        if fname in stat.name:
            return stat
    return None
    
def assert_raises_exception(func):
    try:
        _run(func)
        assert 0 == 1
    except:
        pass

def run_with_yappi(func):
    import yappi
    yappi.start()
    _run(func)
    yappi.stop()
    return yappi.get_stats()