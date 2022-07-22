from enum import Enum, unique, auto
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, Generic, ParamSpec, TypeVar

from bolinette.core.init import InitFunction
from bolinette.core.exceptions import InitError

P = ParamSpec("P")
T_Cls = TypeVar("T_Cls")
T_Default = TypeVar("T_Default")


@unique
class InjectionStrategy(Enum):
    Transcient = auto()
    Scoped = auto()
    Singleton = auto()


class RegisteredType(Generic[T_Cls]):
    def __init__(
        self,
        cls: type[T_Cls],
        strategy: InjectionStrategy,
        func: Callable[[T_Cls], None] | None,
        params: dict[str, Any] | None,
    ) -> None:
        self.cls = cls
        self.strategy = strategy
        self.func = func
        self.params = params


class Cache:
    def __init__(self) -> None:
        self._types: dict[type, RegisteredType[Any]] = {}
        self._names: dict[str, type[Any]] = {}
        self._init_funcs: list[InitFunction] = []

    def add_type(
        self,
        cls: type[T_Cls],
        strategy: InjectionStrategy,
        func: Callable[[T_Cls], None] | None,
        params: dict[str, Any] | None,
    ) -> None:
        self._types[cls] = RegisteredType(cls, strategy, func, params)
        self._names[f'{cls.__module__}.{cls.__name__}'] = cls

    def find_types_by_name(self, name: str) -> list[type[Any]]:
        return [t for n, t in self._names.items() if n.endswith(name)]

    def of_type(self, cls: type[T_Cls]) -> list[type[T_Cls]]:
        return [t for t in self._types if issubclass(t, cls)]

    def has_type(self, cls: type[Any]) -> bool:
        return cls in self._types

    def get_type(self, cls: type[T_Cls]) -> RegisteredType[T_Cls]:
        if cls not in self._types:
            raise KeyError(cls)
        return self._types[cls]

    def add_init_func(self, func: InitFunction) -> None:
        self._init_funcs.append(func)

    @property
    def init_funcs(self) -> list[InitFunction]:
        return [f for f in self._init_funcs]

    @property
    def types(self) -> dict[type, RegisteredType[Any]]:
        return {k: v for k, v in self._types.items()}


__core_cache__ = Cache()


def init_func(
    *, cache: Cache | None = None
) -> Callable[[Callable[P, Awaitable[None]]], Callable[P, Awaitable[None]]]:
    def decorator(func: Callable[P, Awaitable[None]]) -> Callable[P, Awaitable[None]]:
        (cache or __core_cache__).add_init_func(InitFunction(func))
        return func

    return decorator


def injectable(
    *,
    strategy: InjectionStrategy = InjectionStrategy.Singleton,
    func: Callable[[T_Cls], None] | None = None,
    params: dict[str, Any] | None = None,
    cache: Cache | None = None,
) -> Callable[[type[T_Cls]], type[T_Cls]]:
    def decorator(cls: type[T_Cls]) -> type[T_Cls]:
        if not inspect.isclass(cls):
            raise InitError(
                f"'{cls}' must be a class to be decorated by @{injectable.__name__}"
            )
        (cache or __core_cache__).add_type(cls, strategy, func, params)
        return cls

    return decorator
