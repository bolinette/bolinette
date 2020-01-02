import sys

from bolinette import env
from bolinette.cli import cli_env


def run_server(**_):
    bolinette = cli_env['bolinette']
    sys.argv = [sys.argv[0], 'runserver']
    bolinette.app.run(host=env['FLASK_HOST'], port=env['FLASK_PORT'])
