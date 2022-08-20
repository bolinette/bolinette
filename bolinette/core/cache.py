from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, overload

from bolinette.core.init import InitFunction

P = ParamSpec("P")
T_Instance = TypeVar("T_Instance")


class Cache:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._bag: dict[Any, list[Any]] = {}

    def __contains__(self, key: Any) -> bool:
        return key in self._bag

    @overload
    def __getitem__(self, args: tuple[Any, type[T_Instance]], /) -> list[T_Instance]:
        pass

    @overload
    def __getitem__(self, key: Any, /) -> list[Any]:
        pass

    def __getitem__(
        self, args: tuple[Any, type[T_Instance]] | Any, /
    ) -> list[T_Instance] | list[Any]:
        key = None
        match args:
            case (_k, _):
                key = _k
            case _k:
                key = _k
        if key not in self:
            raise KeyError(key)
        return self._bag[key]

    def __delitem__(self, key: Any) -> None:
        if key not in self:
            raise KeyError(key)
        del self._bag[key]

    def init(self, key: Any) -> None:
        self._bag[key] = []

    def add(self, key: Any, value: Any) -> None:
        if key not in self:
            self.init(key)
        self._bag[key].append(value)

    def remove(self, key: Any, value: Any) -> None:
        if key not in self:
            raise KeyError(key)
        self._bag[key] = list(filter(lambda i: i is not value, self._bag[key]))


__core_cache__ = Cache()


def init_func(
    *, cache: Cache | None = None
) -> Callable[[Callable[P, Awaitable[None]]], Callable[P, Awaitable[None]]]:
    def decorator(func: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
        (cache or __core_cache__).add(InitFunction, InitFunction(func))
        return func

    return decorator
