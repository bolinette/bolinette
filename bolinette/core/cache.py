import inspect
from collections.abc import Awaitable, Callable, Iterable, Iterator
from enum import Enum, auto, unique
from typing import Any, ParamSpec, TypeVar

from bolinette.core.exceptions import InitError
from bolinette.core.init import InitFunction

P = ParamSpec("P")
T_Instance = TypeVar("T_Instance")


@unique
class InjectionStrategy(Enum):
    Transcient = auto()
    Scoped = auto()
    Singleton = auto()


class Cache:
    def __init__(self, *, debug: bool = False) -> None:
        self._debug = debug
        self.types = _TypeCache()
        self.bag = _ParameterBag()
        self._init_funcs: list[InitFunction] = []
        self._env_sections: dict[str, type[Any]] = {}

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self._debug = value

    def add_init_func(self, func: InitFunction) -> None:
        self._init_funcs.append(func)

    @property
    def init_funcs(self) -> list[InitFunction]:
        return [f for f in self._init_funcs]

    def add_env_section(self, name: str, cls: type[Any]) -> None:
        self._env_sections[name] = cls

    @property
    def env_sections(self) -> list[tuple[str, type[Any]]]:
        return [(n, c) for n, c in self._env_sections.items()]


class _TypeCache(Iterable[type[Any]]):
    def __init__(self) -> None:
        self._types: set[type[Any]] = set()
        self._strategies: dict[type[Any], InjectionStrategy] = {}
        self._args: dict[type[Any], list[Any]] = {}
        self._kwargs: dict[type[Any], dict[str, Any]] = {}
        self._init_methods: dict[type[Any], list[Callable[[T_Instance], None]]] = {}

    def add(
        self,
        cls: type[T_Instance],
        strategy: InjectionStrategy,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        init_methods: list[Callable[[T_Instance], None]] | None = None,
    ):
        if not isinstance(cls, type):
            raise TypeError(cls)
        self._types.add(cls)
        self._strategies[cls] = strategy
        self._args[cls] = args or []
        self._kwargs[cls] = kwargs or {}
        self._init_methods[cls] = init_methods or []

    def __contains__(self, cls: type[Any]) -> bool:
        return cls in self._types

    def __len__(self) -> int:
        return len(self._types)

    def __iter__(self) -> Iterator[type[Any]]:
        return (t for t in self._types)

    def of_type(self, cls: type[T_Instance]) -> list[type[T_Instance]]:
        return [t for t in self._types if issubclass(t, cls)]

    def strategy(self, cls: type[Any]) -> InjectionStrategy:
        if cls not in self:
            raise KeyError(cls)
        return self._strategies[cls]

    def args(self, cls: type[Any]) -> list[Any]:
        if cls not in self:
            raise KeyError(cls)
        return self._args[cls]

    def kwargs(self, cls: type[Any]) -> dict[str, Any]:
        if cls not in self:
            raise KeyError(cls)
        return self._kwargs[cls]

    def init_methods(self, cls: type[Any]) -> list[Callable[[T_Instance], None]]:
        if cls not in self:
            raise KeyError(cls)
        return self._init_methods[cls]


class _ParameterBag:
    def __init__(self) -> None:
        self._bag: dict[Any, list[Any]] = {}

    def __contains__(self, key: Any) -> bool:
        return key in self._bag

    def __getitem__(self, key: Any) -> list[Any]:
        if key not in self:
            raise KeyError(key)
        return self._bag[key]

    def __delitem__(self, key: Any) -> None:
        if key not in self:
            raise KeyError(key)
        del self._bag[key]

    def push(self, key: Any, value: Any) -> None:
        if key not in self:
            self._bag[key] = []
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
        (cache or __core_cache__).add_init_func(InitFunction(func))
        return func

    return decorator


def injectable(
    *,
    strategy: InjectionStrategy = InjectionStrategy.Singleton,
    args: list[Any] | None = None,
    kwargs: dict[str, Any] | None = None,
    cache: Cache | None = None,
) -> Callable[[type[T_Instance]], type[T_Instance]]:
    def decorator(cls: type[T_Instance]) -> type[T_Instance]:
        if not inspect.isclass(cls):
            raise InitError(
                f"'{cls}' must be a class to be decorated by @{injectable.__name__}"
            )
        (cache or __core_cache__).types.add(cls, strategy, args, kwargs)
        return cls

    return decorator
