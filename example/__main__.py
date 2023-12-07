import asyncio
import sys

from example import make_bolinette

if __name__ == "__main__":
    blnt = make_bolinette()
    asyncio.run(blnt.exec_args(sys.argv[1:]), debug=True)
