import asyncio
import sys

from example import make_bolinette

blnt = make_bolinette()
asyncio.run(blnt.exec_args(sys.argv[1:]), debug=True)
