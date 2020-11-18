import bolinette
from bolinette import testing
from bolinette.commands import command


@command('run_tests')
def run_tests(blnt: 'bolinette.Bolinette', args):
    runner = testing.TestRunner(blnt.context, list(args))
    runner.run_tests(blnt)
