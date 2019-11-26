import unittest
import sys

if __name__ == '__main__':
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner()
    if sys.version_info[0] == 3 and sys.version_info[1] >= 3:
        test_suite = test_loader.discover('tests')
    else:
        test_suite = test_loader.loadTestsFromName('tests.test_functionality')
    #test_suite = test_loader.loadTestsFromName(
    #    'tests.test_tags.MultiThreadTests.test_tagging_cputime'
    #)
    result = test_runner.run(test_suite)
    sys.exit(not result.wasSuccessful())
