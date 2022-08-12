import asyncio
from bolinette.core import Bolinette, command, Logger


@command('hello', 'Says hello')
@command.argument('argument', 'name')
async def test(name: str):
    print('hello', name)


if __name__ == '__main__':
    blnt = Bolinette()

    logger = blnt.injection.require(Logger)
    logger.info('Info message')
    logger.debug('Info message')
    logger.warning('Info message')
    logger.error('Info message')

    asyncio.run(blnt.exec_cmd_args())
