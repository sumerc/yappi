import re
import subprocess
import sys
import unittest
import time

import yappi
import utils


def a():
    pass


class ContextIdCallbackTest(utils.YappiUnitTestCase):
    """Test yappi.set_context_id_callback()."""

    def test_profile_single_context(self):

        def id_callback():
            return self.callback_count

        def a():
            pass

        self.callback_count = 1
        yappi.set_context_id_callback(id_callback)
        yappi.start(profile_threads=False)
        a()  # context-id:1
        self.callback_count = 2
        a()  # context-id:2
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, "a")
        self.assertEqual(fsa.ncall, 1)
        yappi.stop()
        yappi.clear_stats()

        self.callback_count = 1
        yappi.start()  # profile_threads=True
        a()  # context-id:1
        self.callback_count = 2
        a()  # context-id:2
        stats = yappi.get_func_stats()
        fsa = utils.find_stat_by_name(stats, "a")
        self.assertEqual(fsa.ncall, 2)

    def test_bad_input(self):
        self.assertRaises(TypeError, yappi.set_context_id_callback, 1)

    def test_clear_callback(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            return 1

        yappi.set_context_id_callback(callback)
        yappi.start()
        a()
        yappi.set_context_id_callback(None)
        old_callback_count = self.callback_count
        a()
        yappi.stop()

        self.assertEqual(old_callback_count, self.callback_count)

    def test_callback_error(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            raise Exception('callback error')

        yappi.set_context_id_callback(callback)
        yappi.start()
        a()
        a()
        yappi.stop()

        # Callback was cleared after first error.
        self.assertEqual(1, self.callback_count)

    def test_callback_non_integer(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            return None  # Supposed to return an integer.

        yappi.set_context_id_callback(callback)
        yappi.start()
        a()
        a()
        yappi.stop()

        # Callback was cleared after first error.
        self.assertEqual(1, self.callback_count)

    def test_callback(self):
        self.context_id = 0
        yappi.set_context_id_callback(lambda: self.context_id)
        yappi.start()
        a()
        self.context_id = 1
        a()
        self.context_id = 2
        a()

        # Re-schedule context 1.
        self.context_id = 1
        a()
        yappi.stop()

        threadstats = yappi.get_thread_stats().sort('id', 'ascending')
        self.assertEqual(3, len(threadstats))
        self.assertEqual(0, threadstats[0].id)
        self.assertEqual(1, threadstats[1].id)
        self.assertEqual(2, threadstats[2].id)

        self.assertEqual(1, threadstats[0].sched_count)
        self.assertEqual(2, threadstats[1].sched_count)  # Context 1 ran twice.
        self.assertEqual(1, threadstats[2].sched_count)

        funcstats = yappi.get_func_stats()
        self.assertEqual(4, utils.find_stat_by_name(funcstats, 'a').ncall)

    def test_pause_resume(self):
        yappi.set_context_id_callback(lambda: self.context_id)
        yappi.set_clock_type('wall')

        # Start in context 0.
        self.context_id = 0
        yappi.start()
        time.sleep(0.08)

        # Switch to context 1.
        self.context_id = 1
        time.sleep(0.05)

        # Switch back to context 0.
        self.context_id = 0
        time.sleep(0.07)

        yappi.stop()

        t_stats = yappi.get_thread_stats().sort('id', 'ascending')
        self.assertEqual(2, len(t_stats))
        self.assertEqual(0, t_stats[0].id)
        self.assertEqual(2, t_stats[0].sched_count)
        self.assertTrue(0.15 < t_stats[0].ttot < 0.5, t_stats[0].ttot)

        self.assertEqual(1, t_stats[1].id)
        self.assertEqual(1, t_stats[1].sched_count)
        # Context 1 was scheduled for 0.05 seconds during the run of the
        # profiler
        self.assert_almost_equal(t_stats[1].ttot, 0.05)


class ContextNameCallbackTest(utils.YappiUnitTestCase):
    """ Test yappi.set_context_name_callback(). """

    def tearDown(self):
        yappi.set_context_name_callback(None)
        super(ContextNameCallbackTest, self).tearDown()

    def test_bad_input(self):
        self.assertRaises(TypeError, yappi.set_context_name_callback, 1)

    def test_clear_callback(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            return 'name'

        yappi.set_context_name_callback(callback)
        yappi.start()
        a()
        yappi.set_context_name_callback(None)
        old_callback_count = self.callback_count
        a()
        yappi.stop()

        self.assertEqual(old_callback_count, self.callback_count)

    def test_callback_error(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            raise Exception('callback error')

        yappi.set_context_name_callback(callback)
        yappi.start()
        a()
        a()
        yappi.stop()

        # Callback was cleared after first error.
        self.assertEqual(1, self.callback_count)

    def test_callback_none_return(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            if self.callback_count < 3:
                return None  # yappi will call again
            else:
                return "name"

        yappi.set_context_name_callback(callback)
        yappi.start()
        a()
        a()
        yappi.stop()

        # yappi tried again until a string was returned
        self.assertEqual(3, self.callback_count)

    def test_callback_non_string(self):
        self.callback_count = 0

        def callback():
            self.callback_count += 1
            return 1  # Supposed to return a string.

        yappi.set_context_name_callback(callback)
        yappi.start()
        a()
        a()
        yappi.stop()

        # Callback was cleared after first error.
        self.assertEqual(1, self.callback_count)

    def test_callback(self):
        self.context_id = 0
        self.context_name = 'a'
        yappi.set_context_id_callback(lambda: self.context_id)
        yappi.set_context_name_callback(lambda: self.context_name)
        yappi.start()
        a()
        self.context_id = 1
        self.context_name = 'b'
        a()

        # Re-schedule context 0.
        self.context_id = 0
        self.context_name = 'a'
        a()
        yappi.stop()

        threadstats = yappi.get_thread_stats().sort('name', 'ascending')
        self.assertEqual(2, len(threadstats))
        self.assertEqual(0, threadstats[0].id)
        self.assertEqual('a', threadstats[0].name)
        self.assertEqual(1, threadstats[1].id)
        self.assertEqual('b', threadstats[1].name)


if __name__ == '__main__':
    unittest.main()
