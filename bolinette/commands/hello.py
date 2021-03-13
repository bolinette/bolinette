import bolinette
from bolinette import Console
from bolinette.blnt import Transaction
from bolinette.decorators import command


@command('hello', 'Says hello!')
@command.argument('argument', 'name', summary='Who I am greeting?')
async def hello(blnt: 'bolinette.Bolinette', name: str):
    console = Console()
    console.print(f'Hello {name}!')
