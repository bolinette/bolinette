from collections.abc import Callable

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.events import Event, EventListener


class EventMeta:
    def __init__(self, event: Event | str) -> None:
        self.event: str = event


def on_event[FuncT: EventListener](event: Event | str, *, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    def decorator(func: FuncT) -> FuncT:
        (cache or __user_cache__).add(EventMeta, func)
        meta.set(func, EventMeta(event))
        return func

    return decorator


def on_initialized[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event("initialized", cache=cache)


def on_started[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event("started", cache=cache)


def on_stopped[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event("stopped", cache=cache)


def on_error[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event("error", cache=cache)
