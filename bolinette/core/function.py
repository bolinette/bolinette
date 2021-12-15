from collections.abc import Callable, Awaitable

from bolinette import abc


class InitFunction:
    def __init__(self, func: Callable[[abc.Context], Awaitable[None]], rerun_for_tests: bool):
        self._func = func
        self._rerun_for_tests = rerun_for_tests

    @property
    def rerun_for_tests(self):
        return self._rerun_for_tests

    @property
    def name(self):
        return self._func.__name__

    def __call__(self, context: abc.Context):
        return self._func(context)

    def __str__(self):
        return self.name
