from typing import Any, Callable, ParamSpec, Protocol, TypeVar

from bolinette import meta

MdlwInitP = ParamSpec("MdlwInitP")


class Middleware(Protocol[MdlwInitP]):
    def __init__(self, *args: MdlwInitP.args, **kwargs: MdlwInitP.kwargs) -> None:
        ...

    def handle(self) -> None:
        ...


class MiddlewareMeta:
    def __init__(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.args = args
        self.kwargs = kwargs


class MiddlewareBag:
    def __init__(self) -> None:
        self.added: dict[type[Middleware], MiddlewareMeta] = {}
        self.removed: list[type[Middleware]] = []


FuncP = ParamSpec("FuncP")
FuncT = TypeVar("FuncT")


def with_middleware(
    middleware: type[Middleware[MdlwInitP]],
    *args: MdlwInitP.args,
    **kwargs: MdlwInitP.kwargs,
) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    def decorator(func: Callable[FuncP, FuncT]) -> Callable[FuncP, FuncT]:
        if not meta.has(func, MiddlewareBag):
            bag = MiddlewareBag()
            meta.set(func, bag)
        else:
            bag = meta.get(func, MiddlewareBag)
        bag.added[middleware] = MiddlewareMeta(args, kwargs)
        return func

    return decorator


def without_middleware(middleware: type[Middleware]) -> Callable[[Callable[FuncP, FuncT]], Callable[FuncP, FuncT]]:
    def decorator(func: Callable[FuncP, FuncT]) -> Callable[FuncP, FuncT]:
        if not meta.has(func, MiddlewareBag):
            bag = MiddlewareBag()
            meta.set(func, bag)
        else:
            bag = meta.get(func, MiddlewareBag)
        bag.removed.append(middleware)
        return func

    return decorator
