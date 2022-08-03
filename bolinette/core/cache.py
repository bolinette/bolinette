import inspect
from collections.abc import Awaitable, Callable
from enum import Enum, auto, unique
from typing import Any, Generic, ParamSpec, TypeVar

from bolinette.core.exceptions import InitError
from bolinette.core.init import InitFunction

P = ParamSpec("P")
T_Instance = TypeVar("T_Instance")


@unique
class InjectionStrategy(Enum):
    Transcient = auto()
    Scoped = auto()
    Singleton = auto()


class RegisteredType(Generic[T_Instance]):
    def __init__(
        self,
        cls: type[T_Instance],
        strategy: InjectionStrategy,
        args: list[Any] | None,
        kwargs: dict[str, Any] | None,
        init_methods: list[Callable[[T_Instance], None]] | None,
    ) -> None:
        self.cls = cls
        self.strategy = strategy
        self.args = args or []
        self.kwargs = kwargs or {}
        self.init_methods = init_methods or []


class Cache:
    def __init__(self, *, debug: bool = False) -> None:
        self._debug = debug
        self._types: dict[type, RegisteredType[Any]] = {}
        self._names: dict[str, type[Any]] = {}
        self._init_funcs: list[InitFunction] = []
        self._env_sections: dict[str, type[Any]] = {}

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool) -> None:
        self._debug = value

    def add_type(
        self,
        cls: type[T_Instance],
        strategy: InjectionStrategy,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        init_methods: list[Callable[[T_Instance], None]] | None = None,
    ) -> RegisteredType[T_Instance]:
        r_type = RegisteredType(cls, strategy, args, kwargs, init_methods)
        self._types[cls] = r_type
        self._names[f"{cls.__module__}.{cls.__name__}"] = cls
        return r_type

    def get_type(self, cls: type[T_Instance]) -> RegisteredType[T_Instance]:
        if cls not in self._types:
            raise KeyError(cls)
        return self._types[cls]

    def find_types_by_name(self, name: str) -> list[type[Any]]:
        return [t for n, t in self._names.items() if n.endswith(name)]

    def of_type(self, cls: type[T_Instance]) -> list[type[T_Instance]]:
        return [t for t in self._types if issubclass(t, cls)]

    def has_type(self, cls: type[Any]) -> bool:
        return cls in self._types

    @property
    def types(self) -> dict[type, RegisteredType[Any]]:
        return {k: v for k, v in self._types.items()}

    def add_init_func(self, func: InitFunction) -> None:
        self._init_funcs.append(func)

    @property
    def init_funcs(self) -> list[InitFunction]:
        return [f for f in self._init_funcs]

    def add_env_section(self, name: str, cls: type[Any]):
        self._env_sections[name] = cls

    @property
    def env_sections(self) -> list[tuple[str, type[Any]]]:
        return [(n, c) for n, c in self._env_sections.items()]


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
        (cache or __core_cache__).add_type(cls, strategy, args, kwargs)
        return cls

    return decorator
