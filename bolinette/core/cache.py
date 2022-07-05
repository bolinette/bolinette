import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, ParamSpec, TypeVar

from bolinette.core import InitFunction
from bolinette.core.exceptions import InitError

P = ParamSpec("P")
T_Cls = TypeVar("T_Cls")


class Cache:
    def __init__(self) -> None:
        self._types: set[type[Any]] = set()
        self._init_funcs: list[InitFunction] = []

    def add_type(self, _type: type[Any], *args: type[Any]) -> None:
        self._types.add(_type)
        for _t in args:
            self.add_type(_t)

    def add_init_finc(self, func: InitFunction) -> None:
        self._init_funcs.append(func)

    def of_type(self, _type: type[T_Cls]) -> Iterable[type[T_Cls]]:
        return (t for t in self._types if issubclass(t, _type))

    @property
    def init_funcs(self) -> Iterable[InitFunction]:
        return (f for f in self._init_funcs)

    @property
    def types(self) -> Iterable[type[Any]]:
        return (t for t in self._types)


__core_cache__ = Cache()


def init_func():
    def decorator(func: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
        if not inspect.iscoroutinefunction(func):
            raise InitError(
                f"{func} must be an async function to be decorated by @{init_func.__name__}"
            )
        init_func = InitFunction(func)
        __core_cache__.add_init_finc(init_func)
        return func

    return decorator


def injectable():
    def decorator(cls: type[T_Cls]) -> type[T_Cls]:
        if not inspect.isclass(cls):
            raise InitError(
                f"{cls} must be a class to be decorated by @{injectable.__name__}"
            )
        __core_cache__.add_type(cls)
        return cls

    return decorator
