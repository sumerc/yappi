import unittest
import yappi
import threading
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io

import sys


class MultiThreadTests(YappiUnitTestCase):

    def test_simple_tagging(self):

        def ctx_id_cbk():
            cthread = threading.current_thread()
            try:
                return cthread._tag
            except:
                # therre are some dummythreads that might have no _tags associated
                return 0

        def tag_cbk():
            cthread = threading.current_thread()
            try:
                return cthread._tag
            except:
                return -1

        def a():
            print("thread start", threading.current_thread()._tag)
            burn_cpu(0.4)
            print("thread end", threading.current_thread()._tag)

        def b():
            pass

        _TCOUNT = 5

        #sys.setswitchinterval(1000)
        ts = []
        yappi.set_clock_type("wall")
        threading.current_thread()._tag = 0
        yappi.set_tag_callback(tag_cbk)
        #yappi.set_context_id_callback(ctx_id_cbk)
        yappi.start()
        for i in range(_TCOUNT):
            t = threading.Thread(target=a)
            t._tag = i + 1
            ts.append(t)

        for t in ts:
            t.start()

        for t in ts:
            t.join()

        yappi.stop()

        stats = yappi.get_func_stats(filter={'tag': 1})
        stats.print_all()
        #yappi.get_thread_stats().print_all()


class SingleThreadTests(YappiUnitTestCase):

    def test_invalid_tag(self):

        def tag_cbk():
            return -1  # reserved val.

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
        ../yappi/tests/utils.py:125 burn_cpu  2      0.145467  0.200099  0.100049
        '''
        self.assert_traces_almost_equal(t1, traces)

        tagged_traces = yappi.get_func_stats(filter={'tag': 1})
        t1 = '''
        ../yappi/tests/utils.py:125 burn_cpu  1      0.073759  0.100028  0.100028
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
        ..p/yappi/tests/utils.py:134 burn_io  2      0.000021  0.208146  0.104073
        '''
        self.assert_traces_almost_equal(t1, traces)

        tagged_traces = yappi.get_func_stats(filter={'tag': 2})
        t1 = '''
        ..p/yappi/tests/utils.py:134 burn_io  1      0.000007  0.105063  0.105063
        '''
        self.assert_traces_almost_equal(t1, tagged_traces)

        yappi.clear_stats()
