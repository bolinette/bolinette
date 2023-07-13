from typing import Any, Callable, Concatenate, ParamSpec, TypeVar, get_origin

from bolinette import Cache, __user_cache__, meta
from bolinette.injection.hook import InjectionHook
from bolinette.injection.registration import InjectionStrategy
from bolinette.types import Type

FuncP = ParamSpec("FuncP")
InstanceT = TypeVar("InstanceT")
InjectionSymbol = object()


class InitMethodMeta:
    pass


def init_method(func: Callable[Concatenate[InstanceT, FuncP], None]) -> Callable[Concatenate[InstanceT, FuncP], None]:
    meta.set(func, InitMethodMeta())
    return func


class InjectionParamsMeta:
    __slots__ = ("strategy", "args", "named_args", "before_init", "after_init", "match_all")

    def __init__(
        self,
        strategy: InjectionStrategy,
        args: list[Any] | None,
        named_args: dict[str, Any] | None,
        before_init: list[Callable[[InstanceT], None]] | None,
        after_init: list[Callable[[InstanceT], None]] | None,
        match_all: bool,
    ) -> None:
        self.strategy = strategy
        self.args = args or []
        self.named_args = named_args or {}
        self.before_init = before_init or []
        self.after_init = after_init or []
        self.match_all = match_all


def injectable(
    *,
    strategy: InjectionStrategy = "singleton",
    args: list[Any] | None = None,
    named_args: dict[str, Any] | None = None,
    cache: Cache | None = None,
    before_init: list[Callable[[InstanceT], None]] | None = None,
    after_init: list[Callable[[InstanceT], None]] | None = None,
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


def require(cls: type[InstanceT]) -> Callable[[Callable[..., Any]], InjectionHook[InstanceT]]:
    def decorator(func: Callable[..., Any]) -> InjectionHook[InstanceT]:
        return InjectionHook(Type(cls))

    return decorator
