from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Protocol

from peritype import TWrap, wrap_type

from bolinette.core import meta
from bolinette.web._controller import Controller


class Middleware[**MdlwInitP](Protocol):
    def options(self, *args: MdlwInitP.args, **kwargs: MdlwInitP.kwargs) -> None: ...

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any: ...


class MiddlewareMeta:
    def __init__(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.args = args
        self.kwargs = kwargs


class MiddlewareBag:
    KEY: ClassVar[str] = "__blnt_web_middleware_bag__"

    def __init__(self) -> None:
        self.added: dict[TWrap[Any], MiddlewareMeta] = {}
        self.removed: list[TWrap[Any]] = []


def _get_bag(obj: Any) -> MiddlewareBag:
    if meta.has(obj, MiddlewareBag.KEY):
        existing: MiddlewareBag = meta.get(obj, MiddlewareBag.KEY)
        return existing
    bag = MiddlewareBag()
    meta.set(obj, MiddlewareBag.KEY, bag)
    return bag


def with_middleware[CtrlT: Controller | Callable[..., Any], **MdlwInitP](
    middleware: type[Middleware[MdlwInitP]],
    *args: MdlwInitP.args,
    **kwargs: MdlwInitP.kwargs,
) -> Callable[[CtrlT], CtrlT]:
    def decorator(func: CtrlT) -> CtrlT:
        bag = _get_bag(func)
        bag.added[wrap_type(middleware)] = MiddlewareMeta(args, kwargs)
        return func

    return decorator


def without_middleware[CtrlT: Controller | Callable[..., Any]](
    middleware: type[Middleware[...]],
) -> Callable[[CtrlT], CtrlT]:
    def decorator(func: CtrlT) -> CtrlT:
        bag = _get_bag(func)
        bag.removed.append(wrap_type(middleware))
        return func

    return decorator
