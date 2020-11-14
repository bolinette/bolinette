import sys

from example import bolinette
# noinspection PyUnresolvedReferences
import tests

app = bolinette.app

if __name__ == '__main__':
    bolinette.run_command(sys.argv[1])
