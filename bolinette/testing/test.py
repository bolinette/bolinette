from typing import Callable, Awaitable

from bolinette.testing import TestClient


class Bolitest:
    def __init__(self, func: Callable[[TestClient], Awaitable[None]], file: str):
        self.func = func
        self.name = None
        self._func_name = func.__name__
        self._file = file

    def set_name(self, root_path):
        self.name = self._file.replace(root_path + '/', '').replace('.py', '') + '::' + self._func_name
