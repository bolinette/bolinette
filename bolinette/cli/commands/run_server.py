import sys

from bolinette.cli import cli_env


def run_server(**_):
    bolinette = cli_env['bolinette']
    sys.argv = [sys.argv[0], 'runserver']
    bolinette.manager.run()
