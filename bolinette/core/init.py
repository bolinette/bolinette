import inspect
from collections.abc import Awaitable, Callable
from typing import Generic, ParamSpec

from bolinette.core.exceptions import InitError

P = ParamSpec("P")


class InitFunction(Generic[P]):
    def __init__(self, func: Callable[P, Awaitable[None]]) -> None:
        if not inspect.iscoroutinefunction(func):
            raise InitError(
                f"'{func}' must be an async function to be an init function"
            )
        self._func = func

    @property
    def name(self) -> str:
        return self._func.__name__

    @property
    def function(self) -> Callable[P, Awaitable[None]]:
        return self._func

    def __str__(self) -> str:
        return self.name

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> Awaitable[None]:
        return self._func(*args, **kwargs)
