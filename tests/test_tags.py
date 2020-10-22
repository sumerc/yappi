import unittest
import yappi
import threading
import time
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io


class MultiThreadTests(YappiUnitTestCase):

    def test_tagging_walltime(self):
        tlocal = threading.local()

        def tag_cbk():
            try:
                return tlocal._tag
            except Exception as e:
                #print(e)
                return -1

        def a(tag):
            tlocal._tag = tag

            burn_io(0.1)

        _TCOUNT = 20

        yappi.set_clock_type("wall")
        tlocal._tag = 0
        yappi.set_tag_callback(tag_cbk)
        yappi.start()

        ts = []
        for i in range(_TCOUNT):
            t = threading.Thread(target=a, args=(i + 1, ))
            ts.append(t)

        for t in ts:
            t.start()

        for t in ts:
            t.join()

        yappi.stop()

        traces = yappi.get_func_stats()
        t1 = '''
        ..p/yappi/tests/utils.py:134 burn_io  20     0.000638  2.004059  0.100203
        '''
        self.assert_traces_almost_equal(t1, traces)

        traces = yappi.get_func_stats(filter={'tag': 3})
        t1 = '''
        ..p/yappi/tests/utils.py:134 burn_io  1      0.000038  0.100446  0.100446
        '''
        self.assert_traces_almost_equal(t1, traces)

    def test_tagging_cputime(self):

        tlocal = threading.local()

        def tag_cbk():
            try:
                return tlocal._tag
            except Exception as e:
                #print(e)
                return -1

        def a(tag):
            tlocal._tag = tag

            burn_cpu(0.1)

        _TCOUNT = 5

        ts = []
        yappi.set_clock_type("cpu")
        tlocal._tag = 0
        yappi.set_tag_callback(tag_cbk)
        yappi.start()
        for i in range(_TCOUNT):
            t = threading.Thread(target=a, args=(i + 1, ))
            ts.append(t)

        for t in ts:
            t.start()

        for t in ts:
            t.join()

        yappi.stop()

        traces = yappi.get_func_stats()
        t1 = '''
        ..op/p/yappi/tests/test_tags.py:21 a  5      0.000137  0.500562  0.000000
        ../yappi/tests/utils.py:125 burn_cpu  5      0.000000  0.500424  0.000000
        '''
        self.assert_traces_almost_equal(t1, traces)

        traces = yappi.get_func_stats(filter={'tag': 1})
        t1 = '''
        ../yappi/tests/utils.py:125 burn_cpu  1      0.000000  0.100125  0.100125
        '''
        self.assert_traces_almost_equal(t1, traces)

        traces = yappi.get_func_stats(filter={'tag': 3})
        t1 = '''
        ../yappi/tests/utils.py:125 burn_cpu  1      0.000000  0.100128  0.100128
        '''
        self.assert_traces_almost_equal(t1, traces)


class SingleThreadTests(YappiUnitTestCase):

    def test_invalid_tag(self):

        def tag_cbk():
            return -1

        yappi.set_tag_callback(tag_cbk)
        yappi.start()
        tag_cbk()
        yappi.stop()
        stats = yappi.get_func_stats()
        stat = find_stat_by_name(stats, 'tag_cbk')
        self.assertEqual(stat.ncall, 1)

    def test_simple_tagging(self):

        def tag_cbk():
            return 1

        def tag_cbk2():
            return 2

        # test cpu-time
        yappi.set_tag_callback(tag_cbk)
        yappi.start()
        burn_cpu(0.1)
        yappi.set_tag_callback(tag_cbk2)
        burn_cpu(0.1)
        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        ../yappi/tests/utils.py:125 burn_cpu  2      0.000000  0.200156  0.100078
        '''
        self.assert_traces_almost_equal(t1, traces)

        tagged_traces = yappi.get_func_stats(filter={'tag': 1})
        t1 = '''
        ../yappi/tests/utils.py:125 burn_cpu  1      0.000000  0.100062  0.100062
        '''
        self.assert_traces_almost_equal(t1, tagged_traces)

        yappi.clear_stats()

        # test wall
        yappi.set_clock_type("wall")
        yappi.set_tag_callback(tag_cbk)
        yappi.start()
        burn_io(0.1)
        yappi.set_tag_callback(tag_cbk2)
        burn_io(0.1)
        yappi.stop()
        traces = yappi.get_func_stats()
        t1 = '''
        ..p/yappi/tests/utils.py:134 burn_io  2      0.000000  0.208146  0.104073
        '''
        self.assert_traces_almost_equal(t1, traces)

        tagged_traces = yappi.get_func_stats(filter={'tag': 2})
        t1 = '''
        ..p/yappi/tests/utils.py:134 burn_io  1      0.000000  0.105063  0.105063
        '''
        self.assert_traces_almost_equal(t1, tagged_traces)

        yappi.clear_stats()
