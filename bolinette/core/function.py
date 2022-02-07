from collections.abc import Callable, Awaitable

from bolinette import core


class InitFunction:
    def __init__(
        self,
        func: Callable[["core.BolinetteContext"], Awaitable[None]],
        rerunable: bool,
    ):
        self._func = func
        self._rerunable = rerunable

    @property
    def rerunable(self):
        return self._rerunable

    @property
    def name(self):
        return self._func.__name__

    @property
    def function(self):
        return self._func

    def __str__(self):
        return self.name
