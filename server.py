import os
import sys

# noinspection PyUnresolvedReferences
import tests

if __name__ == '__main__':
    command = sys.argv[1]
    if command == 'run_tests':
        if 'BLNT_PROFILE' not in os.environ:
            os.environ['BLNT_PROFILE'] = 'test'
    from example import bolinette
    bolinette.run_command(command)
