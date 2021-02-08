import bolinette
from bolinette.decorators import command


@command('run_server', 'Run the internal server')
@command.argument('option', 'host', flag='H', summary='The host the server will listen to')
@command.argument('option', 'port', flag='p', summary='The port the server will listen on', value_type=int)
def run_server(blnt: 'bolinette.Bolinette', host: str = None, port: int = None):
    blnt.start_server(host=host, port=port)
