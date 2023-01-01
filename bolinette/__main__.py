import asyncio

from bolinette import Bolinette

blnt = Bolinette()
asyncio.run(blnt.exec_cmd_args())
