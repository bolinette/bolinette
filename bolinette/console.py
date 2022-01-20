import sys


class Console:
    def __init__(self, *, flush: bool = False, debug: bool = False):
        self._flush = flush
        self._debug = debug

    def print(self, *values, sep=' ', end='\n'):
        print(*values, sep=sep, end=end, flush=self._flush)

    def error(self, *values, sep=' ', end='\n'):
        print(*values, file=sys.stderr, sep=sep, end=end, flush=self._flush)

    def debug(self, *values, sep=' ', end='\n'):
        if self._debug:
            self.print(*values, sep=sep, end=end)


console = Console()
