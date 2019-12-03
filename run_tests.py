import unittest
import sys

if __name__ == '__main__':
    sys.path.append('tests/')
    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner()
    tests = ['test_functionality', 'test_hooks', 'test_tags']
    if sys.version_info >= (3, 4):
        tests += ['test_asyncio']
    if sys.version_info >= (3, 7):
        tests += ['test_asyncio_context_vars']
    test_suite = test_loader.loadTestsFromNames(tests)
    result = test_runner.run(test_suite)
    sys.exit(not result.wasSuccessful())
