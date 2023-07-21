from typing import Any, Awaitable, Callable, ParamSpec, Protocol, TypeVar

from aiohttp import web

from bolinette.core import meta
from bolinette.core.types import Type
from bolinette.web import Controller

MdlwInitP = ParamSpec("MdlwInitP")
CtrlT = TypeVar("CtrlT", bound=Controller | Callable[..., Any])


class Middleware(Protocol[MdlwInitP]):
    def options(self, *args: MdlwInitP.args, **kwargs: MdlwInitP.kwargs) -> None:
        ...

    async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
        ...


class MiddlewareMeta:
    def __init__(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.args = args
        self.kwargs = kwargs


class MiddlewareBag:
    def __init__(self) -> None:
        self.added: dict[Type[Middleware[...]], MiddlewareMeta] = {}
        self.removed: list[Type[Middleware[...]]] = []


def with_middleware(
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


def without_middleware(middleware: type[Middleware[...]]) -> Callable[[CtrlT], CtrlT]:
    def decorator(func: CtrlT) -> CtrlT:
        if not meta.has(func, MiddlewareBag):
            bag = MiddlewareBag()
            meta.set(func, bag)
        else:
            bag = meta.get(func, MiddlewareBag)
        bag.removed.append(Type(middleware))
        return func

    return decorator
