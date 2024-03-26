from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from bolinette.core import meta
from bolinette.core.types import Type
from bolinette.web import Controller


class Middleware[**MdlwInitP](Protocol):
    def options(self, *args: MdlwInitP.args, **kwargs: MdlwInitP.kwargs) -> None: ...

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any: ...


class MiddlewareMeta:
    def __init__(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.args = args
        self.kwargs = kwargs


class MiddlewareBag:
    def __init__(self) -> None:
        self.added: dict[Type[Middleware[...]], MiddlewareMeta] = {}
        self.removed: list[Type[Middleware[...]]] = []


def with_middleware[CtrlT: Controller | Callable[..., Any], **MdlwInitP](
    middleware: type[Middleware[MdlwInitP]],
    *args: MdlwInitP.args,
    **kwargs: MdlwInitP.kwargs,
) -> Callable[[CtrlT], CtrlT]:
    def decorator(func: CtrlT) -> CtrlT:
        if not meta.has(func, MiddlewareBag):
            bag = MiddlewareBag()
            meta.set(func, bag)
        else:
            bag = meta.get(func, MiddlewareBag)
        bag.added[Type(middleware)] = MiddlewareMeta(args, kwargs)
        return func

    return decorator


def without_middleware[CtrlT: Controller | Callable[..., Any]](
    middleware: type[Middleware[...]],
) -> Callable[[CtrlT], CtrlT]:
    def decorator(func: CtrlT) -> CtrlT:
        if not meta.has(func, MiddlewareBag):
            bag = MiddlewareBag()
            meta.set(func, bag)
        else:
            bag = meta.get(func, MiddlewareBag)
        bag.removed.append(Type(middleware))
        return func

    return decorator
