import sys
import yappi
import time
import unittest


class YappiUnitTestCase(unittest.TestCase):

    def setUp(self):
        # reset everything back to default
        yappi.stop()
        yappi.clear_stats()
        yappi.set_clock_type('cpu')  # reset to default clock type
        yappi.set_context_backend('native_thread')
        yappi.set_context_id_callback(None)
        yappi.set_context_name_callback(None)
        yappi.set_tag_callback(None)

    def tearDown(self):
        fstats = yappi.get_func_stats()
        if not fstats._debug_check_sanity():
            sys.stdout.write("ERR: Duplicates found in Func stats\r\n")

            fstats.debug_print()
        for fstat in fstats:
            if not fstat.children._debug_check_sanity():
                sys.stdout.write("ERR: Duplicates found in ChildFunc stats\r\n")
                fstat.children.print_all()
        tstats = yappi.get_func_stats()
        if not tstats._debug_check_sanity():
            sys.stdout.write("ERR: Duplicates found in Thread stats\r\n")
            tstats.print_all()

    def assert_traces_almost_equal(self, traces_str, traces):
        for t in traces_str.split('\n'):
            tline = t.strip()
            if tline:
                t = tline.split()
                ttot_orig = float(t[-2].strip())
                tsub_orig = float(t[-3].strip())
                ncall_orig = t[-4].strip()

                if '/' in ncall_orig:  # recursive func?
                    ncall_orig = ncall_orig.split('/')
                    ncall = int(ncall_orig[0])
                    non_recursive_ncall = int(ncall_orig[1])
                else:
                    ncall = int(ncall_orig)
                    non_recursive_ncall = ncall

                t = find_stat_by_name(traces, t[-5])
                self.assertEqual(ncall, t.ncall, tline)
                self.assertEqual(non_recursive_ncall, t.nactualcall, tline)
                if ttot_orig:
                    self.assert_almost_equal(ttot_orig, t.ttot, err_msg=tline)
                if tsub_orig:
                    self.assert_almost_equal(tsub_orig, t.tsub, err_msg=tline)

    def assert_ctx_stats_almost_equal(self, expected_stats_str, actual_stats):
        for t in expected_stats_str.split('\n'):
            tline = t.strip()
            if tline:
                t = tline.split()
                ttot_orig = float(t[-2].strip())

                ctx = find_ctx_stats_by_name(actual_stats, t[0])
                if ttot_orig:
                    self.assert_almost_equal(ttot_orig, ctx.ttot, err_msg=tline)

    def assert_almost_equal(
        self, x, y, negative_err=0.2, positive_err=0.6, err_msg=None
    ):
        pos_epsilon = (x * positive_err)
        neg_epsilon = (x * negative_err)

        # if too small, then use 0 as negative threshold
        neg_threshold = x - neg_epsilon
        if neg_threshold < 0.1:
            neg_threshold = 0

        pos_threshold = x + pos_epsilon
        if pos_threshold < 0.1:
            pos_threshold = 0.1

        assert neg_threshold <= y <= pos_threshold, "%s <= %s <= %s is not True. [%s]" % (
            neg_threshold, y, pos_threshold, err_msg
        )


def assert_raises_exception(func):
    try:
        _run(func)
        assert 0 == 1
    except:
        pass


def run_with_yappi(func, *args, **kwargs):
    yappi.start()
    func(*args, **kwargs)
    yappi.stop()


def run_and_get_func_stats(func, *args, **kwargs):
    run_with_yappi(func, *args, **kwargs)
    return yappi.get_func_stats()


def run_and_get_thread_stats(func, *args, **kwargs):
    run_with_yappi(func, *args, **kwargs)
    return yappi.get_thread_stats()


def is_py3x():
    return sys.version_info > (3, 0)


def find_stat_by_name(stats, name):
    for stat in stats:
        if hasattr(stat, 'module'):
            if stat.module + '.' + stat.name == name:
                return stat

        if stat.name == name:
            return stat


def find_ctx_stats_by_name(ctx_stats, name):
    for stat in ctx_stats:
        if stat.name == name:
            return stat


def get_stat_names(stats):
    return [stat.name for stat in stats]


def find_stat_by_id(stats, id):
    for stat in stats:
        if stat.id == id:
            return stat


def burn_cpu(sec):
    t0 = yappi.get_clock_time()
    elapsed = 0
    while (elapsed < sec):
        for _ in range(1000):
            pass
        elapsed = yappi.get_clock_time() - t0


def burn_io(sec):
    time.sleep(sec)


def burn_io_gevent(sec):
    import gevent
    gevent.sleep(sec)


from contextlib import contextmanager


@contextmanager
def captured_output():
    if is_py3x():
        from io import StringIO
    else:
        from StringIO import StringIO

    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err
