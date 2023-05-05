from typing import Any, Callable, Concatenate, Literal, ParamSpec, TypeVar, get_origin

from bolinette import meta, Cache, __user_cache__
from bolinette.types import Type
from bolinette.injection.hook import InjectionHook


FuncP = ParamSpec("FuncP")
InstanceT = TypeVar("InstanceT")
InjectionSymbol = object()


class InitMethodMeta:
    pass


def init_method(func: Callable[Concatenate[InstanceT, FuncP], None]) -> Callable[Concatenate[InstanceT, FuncP], None]:
    meta.set(func, InitMethodMeta())
    return func


class InjectionParamsMeta:
    __slots__ = ("strategy", "args", "named_args", "init_methods", "match_all")

    def __init__(
        self,
        strategy: Literal["singleton", "scoped", "transcient"],
        args: list[Any] | None,
        named_args: dict[str, Any] | None,
        init_methods: list[Callable[[Any], None]] | None,
        match_all: bool,
    ) -> None:
        self.strategy = strategy
        self.args = args or []
        self.named_args = named_args or {}
        self.init_methods = init_methods or []
        self.match_all = match_all


def injectable(
    *,
    strategy: Literal["singleton", "scoped", "transcient"] = "singleton",
    args: list[Any] | None = None,
    named_args: dict[str, Any] | None = None,
    cache: Cache | None = None,
    init_methods: list[Callable[[InstanceT], None]] | None = None,
    match_all: bool = False,
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    def decorator(cls: type[InstanceT]) -> type[InstanceT]:
        if origin := get_origin(cls):
            _cls = origin
        else:
            _cls = cls
        meta.set(_cls, InjectionParamsMeta(strategy, args, named_args, init_methods, match_all))
        (cache or __user_cache__).add(InjectionSymbol, cls)
        return cls

    return decorator


def require(cls: type[InstanceT]) -> Callable[[Callable], InjectionHook[InstanceT]]:
    def decorator(func: Callable) -> InjectionHook[InstanceT]:
        return InjectionHook(Type(cls))

    return decorator
