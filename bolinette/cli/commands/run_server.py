import sys

from bolinette import env


def run_server(bolinette):
    sys.argv = [sys.argv[0], 'runserver']
    bolinette.app.run(host=env['FLASK_HOST'], port=env['FLASK_PORT'])
