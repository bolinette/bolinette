import sys


class Console:
    def __init__(self, *, flush: bool = False):
        self.flush = flush

    def print(self, text: str = None, *, sep=' ', end='\n'):
        print(text or '', sep=sep, end=end, flush=self.flush)

    def error(self, text: str = None, *, sep=' ', end='\n'):
        print(text or '', file=sys.stderr, sep=sep, end=end, flush=self.flush)


console = Console()
