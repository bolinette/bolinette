import sys
# noinspection PyUnresolvedReferences
import tests

if __name__ == '__main__':
    from example import create_app
    bolinette = create_app()
    bolinette.run_command(*sys.argv[1:])
