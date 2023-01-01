import asyncio

from bolinette.core import Bolinette

blnt = Bolinette()
asyncio.run(blnt.exec_cmd_args())
