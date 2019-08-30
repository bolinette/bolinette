import sys

from example import bolinette
from tests.tests import run_tests

if __name__ == '__main__':
    if sys.argv[1] == 'tests':
        run_tests()
    else:
        bolinette.manager.run()
