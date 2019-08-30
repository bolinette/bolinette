import unittest


def run_tests():
    runner = unittest.TextTestRunner(verbosity=2)
    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().discover('tests.controllers', 'Test*'))
    runner.run(suite)
