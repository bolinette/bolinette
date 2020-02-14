import sys


def run_server(parser):
    from bolinette import env
    parser.blnt.app.run(host=env['FLASK_HOST'], port=env['FLASK_PORT'])
