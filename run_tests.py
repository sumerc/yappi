import unittest
import sys


def _testsuite_from_tests(tests):
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    for t in tests:
        test = loader.loadTestsFromName('tests.%s' % (t))
        suite.addTest(test)
    return suite


if __name__ == '__main__':
    sys.path.append('tests/')
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner(verbosity=2)
    tests = ['test_functionality', 'test_hooks', 'test_tags', 'test_gevent']
    if sys.version_info >= (3, 4):
        tests += ['test_asyncio']
    if sys.version_info >= (3, 7):
        tests += ['test_asyncio_context_vars']
    test_suite = test_loader.loadTestsFromNames(tests)

    if len(sys.argv) > 1:
        test_suite = _testsuite_from_tests(sys.argv[1:])

    #tests = ['test_functionality.BasicUsage.test_run_as_script']

    result = test_runner.run(test_suite)
    sys.exit(not result.wasSuccessful())
