import bolinette
from bolinette import testing
from bolinette.commands import command


@command('run_tests')
def run_tests(blnt: 'bolinette.Bolinette'):
    runner = testing.TestRunner()
    runner.run_tests(blnt)
