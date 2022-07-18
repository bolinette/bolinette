import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from bolinette.core import InitFunction
from bolinette.core.exceptions import InitError

P = ParamSpec("P")
T_Cls = TypeVar("T_Cls")
T_Default = TypeVar("T_Default")


class Cache:
    def __init__(self) -> None:
        self._types: set[type[Any]] = set()
        self._init_funcs: list[InitFunction] = []

    def add_type(self, cls: type[Any], *args: type[Any]) -> None:
        self._types.add(cls)
        for _t in args:
            self.add_type(_t)

    def add_init_func(self, func: InitFunction) -> None:
        self._init_funcs.append(func)

    def of_type(self, cls: type[T_Cls]) -> list[type[T_Cls]]:
        return [t for t in self._types if issubclass(t, cls)]

    def has_type(self, cls: type[T_Cls]) -> bool:
        return cls in self._types

    @property
    def init_funcs(self) -> list[InitFunction]:
        return [f for f in self._init_funcs]

    @property
    def types(self) -> list[type[Any]]:
        return [t for t in self._types]


__core_cache__ = Cache()


def init_func(
    *, cache: Cache | None = None
) -> Callable[[Callable[P, Awaitable[None]]], Callable[P, Awaitable[None]]]:
    def decorator(func: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
        (cache or __core_cache__).add_init_func(InitFunction(func))
        return func

    return decorator


def injectable(*, cache: Cache | None = None) -> Callable[[type[T_Cls]], type[T_Cls]]:
    def decorator(cls: type[T_Cls]) -> type[T_Cls]:
        if not inspect.isclass(cls):
            raise InitError(
                f"'{cls}' must be a class to be decorated by @{injectable.__name__}"
            )
        (cache or __core_cache__).add_type(cls)
        return cls

    return decorator
