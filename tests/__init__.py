import unittest
all_tests = unittest.TestLoader().discover('tests')
unittest.TextTestRunner().run(all_tests)