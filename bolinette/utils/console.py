import sys


class Console:
    def print(self, text, *, sep=' ', end='\n'):
        print(text, sep=sep, end=end)

    def error(self, text, *, sep=' ', end='\n'):
        print(text, file=sys.stderr, sep=sep, end=end)


console = Console()
