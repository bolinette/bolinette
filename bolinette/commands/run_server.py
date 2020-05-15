import bolinette
from bolinette.commands import command


@command('run_server')
def run_server(blnt: 'bolinette.Bolinette'):
    blnt.run()
