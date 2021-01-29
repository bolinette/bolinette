import bolinette
from bolinette.blnt.commands import Argument, ArgType
from bolinette.decorators import command


@command('run_server', 'Run the internal server',
         Argument(ArgType.Option, 'host', flag='H', summary='Host the server will listen to'),
         Argument(ArgType.Option, 'port', flag='p', summary='Port the server will listen on', value_type=int))
def run_server(blnt: 'bolinette.Bolinette', host: str, port: int):
    blnt.run(host=host, port=port)
