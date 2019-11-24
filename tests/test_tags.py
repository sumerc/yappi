import unittest
import yappi
from utils import YappiUnitTestCase, find_stat_by_name, burn_cpu, burn_io


class SingleThread(YappiUnitTestCase):

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
        ../yappi/tests/utils.py:125 burn_cpu  2      0.179780  0.198727  0.099363
        '''
        self.assert_traces_almost_equal(t1, traces)

        tagged_traces = yappi.get_func_stats(filter={'tag': 1})
        t1 = '''
        ../yappi/tests/utils.py:125 burn_cpu  1      0.087518  0.096127  0.096127
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
