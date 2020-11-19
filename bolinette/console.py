import sys


class Console:
    def print(self, text: str = None, *, sep=' ', end='\n'):
        print(text or '', sep=sep, end=end)

    def error(self, text: str = None, *, sep=' ', end='\n'):
        print(text or '', file=sys.stderr, sep=sep, end=end)


console = Console()
