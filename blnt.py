import asyncio
from bolinette.core import Bolinette, command


@command('hello', 'Says hello')
@command.argument('argument', 'name')
async def test(name: str):
    print('hello', name)


if __name__ == '__main__':
    blnt = Bolinette()
    asyncio.run(blnt.exec_cmd_args())
