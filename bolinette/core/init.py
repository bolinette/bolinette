from collections.abc import Awaitable, Callable
from typing import ParamSpec

P = ParamSpec("P")


class InitFunction:
    def __init__(self, func: Callable[P, Awaitable[None]]):
        self._func = func

    @property
    def name(self):
        return self._func.__name__

    @property
    def function(self):
        return self._func

    def __str__(self):
        return self.name
