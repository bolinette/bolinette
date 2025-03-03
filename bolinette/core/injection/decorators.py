from collections.abc import Callable
from typing import Any, Concatenate, get_origin

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.injection.hook import InjectionHook
from bolinette.core.injection.registration import AddStrategy
from bolinette.core.types import Type

InjectionSymbol = object()


class PostInitMeta:
    pass


def post_init[InstanceT](
    func: Callable[Concatenate[InstanceT, ...], None],
) -> Callable[Concatenate[InstanceT, ...], None]:
    meta.set(func, PostInitMeta())
    return func


class InjectionParamsMeta:
    def __init__(
        self,
        strategy: AddStrategy,
        interfaces: list[type[Any]] | None,
        args: list[Any] | None,
        named_args: dict[str, Any] | None,
        match_all: bool,
    ) -> None:
        self.strategy = strategy
        self.interfaces = interfaces or []
        self.args = args or []
        self.named_args = named_args or {}
        self.match_all = match_all


class InjectionInitFuncMeta[InstanceT]:
    def __init__(self) -> None:
        self.before_init: list[Callable[Concatenate[InstanceT, ...], None]] = []
        self.after_init: list[Callable[Concatenate[InstanceT, ...], None]] = []


def injectable[InstanceT](
    *,
    strategy: AddStrategy = "singleton",
    interfaces: list[type[Any]] | None = None,
    args: list[Any] | None = None,
    named_args: dict[str, Any] | None = None,
    cache: Cache | None = None,
    match_all: bool = False,
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    def decorator(cls: type[InstanceT]) -> type[InstanceT]:
        if origin := get_origin(cls):
            _cls = origin
        else:
            _cls = cls
        meta.set(_cls, InjectionParamsMeta(strategy, interfaces, args, named_args, match_all))
        (cache or __user_cache__).add(InjectionSymbol, cls)
        return cls

    return decorator


def before_init[InstanceT](
    func: Callable[Concatenate[Any, ...], None], /
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    def decorator(cls: type[InstanceT]) -> type[InstanceT]:
        func_meta: InjectionInitFuncMeta[InstanceT]
        if not meta.has(cls, InjectionInitFuncMeta):
            func_meta = InjectionInitFuncMeta()
            meta.set(cls, func_meta)
        else:
            func_meta = meta.get(cls, InjectionInitFuncMeta)
        func_meta.before_init.append(func)
        return cls

    return decorator


def after_init[InstanceT](
    func: Callable[Concatenate[Any, ...], None], /
) -> Callable[[type[InstanceT]], type[InstanceT]]:
    def decorator(cls: type[InstanceT]) -> type[InstanceT]:
        func_meta: InjectionInitFuncMeta[InstanceT]
        if not meta.has(cls, InjectionInitFuncMeta):
            func_meta = InjectionInitFuncMeta()
            meta.set(cls, func_meta)
        else:
            func_meta = meta.get(cls, InjectionInitFuncMeta)
        func_meta.after_init.append(func)
        return cls

    return decorator


def require[InstanceT](cls: type[InstanceT]) -> Callable[[Callable[..., Any]], InjectionHook[InstanceT]]:
    def decorator(func: Callable[..., Any]) -> InjectionHook[InstanceT]:
        return InjectionHook(Type(cls), False, None)

    return decorator
