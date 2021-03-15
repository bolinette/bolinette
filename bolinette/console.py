import sys


class Console:
    def __init__(self, *, flush: bool = False, debug: bool = False):
        self._flush = flush
        self._debug = debug

    def print(self, text: str = None, *, sep=' ', end='\n'):
        print(text or '', sep=sep, end=end, flush=self._flush)

    def error(self, text: str = None, *, sep=' ', end='\n'):
        print(text or '', file=sys.stderr, sep=sep, end=end, flush=self._flush)

    def debug(self, text: str = None, *, sep=' ', end='\n'):
        if self._debug:
            self.print(text, sep=sep, end=end)


console = Console()
