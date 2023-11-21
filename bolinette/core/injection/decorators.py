from collections.abc import Callable
from typing import Any, Concatenate, get_origin

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.injection.hook import InjectionHook
from bolinette.core.injection.registration import AddStrategy
from bolinette.core.types import Type

InjectionSymbol = object()


class InitMethodMeta:
    pass


def init_method[InstanceT, **FuncP](
    func: Callable[Concatenate[InstanceT, FuncP], None],
) -> Callable[Concatenate[InstanceT, FuncP], None]:
    meta.set(func, InitMethodMeta())
    return func


class InjectionParamsMeta[InstanceT, **FuncP]:
    __slots__ = ("strategy", "args", "named_args", "before_init", "after_init", "match_all")

    def __init__(
        self,
        strategy: AddStrategy,
        args: list[Any] | None,
        named_args: dict[str, Any] | None,
        before_init: list[Callable[Concatenate[InstanceT, FuncP], None]] | None,
        after_init: list[Callable[Concatenate[InstanceT, FuncP], None]] | None,
        match_all: bool,
    ) -> None:
        self.strategy = strategy
        self.args = args or []
        self.named_args = named_args or {}
        self.before_init = before_init or []
        self.after_init = after_init or []
        self.match_all = match_all


def injectable[InstanceT, **FuncP](
    *,
    strategy: AddStrategy = "singleton",
    args: list[Any] | None = None,
    named_args: dict[str, Any] | None = None,
    cache: Cache | None = None,
    before_init: list[Callable[Concatenate[InstanceT, FuncP], None]] | None = None,
    after_init: list[Callable[Concatenate[InstanceT, FuncP], None]] | None = None,
    match_all: bool = False,
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    def decorator(cls: type[InstanceT]) -> type[InstanceT]:
        if origin := get_origin(cls):
            _cls = origin
        else:
            _cls = cls
        meta.set(_cls, InjectionParamsMeta(strategy, args, named_args, before_init, after_init, match_all))
        (cache or __user_cache__).add(InjectionSymbol, cls)
        return cls

    return decorator


def require[InstanceT](cls: type[InstanceT]) -> Callable[[Callable[..., Any]], InjectionHook[InstanceT]]:
    def decorator(func: Callable[..., Any]) -> InjectionHook[InstanceT]:
        return InjectionHook(Type(cls))

    return decorator
