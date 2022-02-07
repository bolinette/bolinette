from abc import ABC, abstractmethod, abstractproperty
from collections.abc import Callable, Awaitable
from typing import Iterable, TypeVar, Generic

from bolinette import core
from bolinette.core import abc, InitFunction, BolinetteCache


class ExtensionContext(abc.WithContext, ABC):
    def __init__(self, ext: "BolinetteExtension", context: "core.BolinetteContext"):
        abc.WithContext.__init__(self, context)
        self.ext = ext


T = TypeVar("T", bound=ExtensionContext)


class BolinetteExtension(ABC, Generic[T]):
    def __init__(self, *, dependencies: list["BolinetteExtension"] = None):
        self._cache = BolinetteCache()
        self._init_funcs: list[InitFunction] = []
        self._dependencies = dependencies or []

    @property
    def cache(self) -> BolinetteCache:
        return self._cache

    @property
    def init_funcs(self) -> Iterable[InitFunction]:
        return (f for f in self._init_funcs)

    @property
    def dependencies(self) -> Iterable["BolinetteExtension"]:
        return (d for d in self._dependencies)

    @abstractmethod
    def __create_context__(self, context: "core.BolinetteContext") -> T:
        ...

    @abstractproperty
    def __context_type__(self) -> type[T]:
        ...

    def init_func(self, *, rerunable: bool = False):
        def decorator(func: Callable[["core.BolinetteContext", T], Awaitable[None]]):
            init_func = InitFunction(func, rerunable)
            self._init_funcs.append(init_func)
            return func

        return decorator

    def __str__(self):
        return type(self).__name__

    def __repr__(self) -> str:
        return str(self)
