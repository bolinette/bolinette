from collections.abc import Callable
from dataclasses import dataclass

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.events import (
    BLNT_ERROR_EVENT,
    BLNT_INITIALIZED_EVENT,
    BLNT_STARTED_EVENT,
    BLNT_STOPPED_EVENT,
    EventListener,
)


@dataclass
class EventMeta:
    event: str
    priority: int


def on_event[FuncT: EventListener](
    event: str,
    /,
    priority: int = 0,
    *,
    cache: Cache | None = None,
) -> Callable[[FuncT], FuncT]:
    def decorator(func: FuncT) -> FuncT:
        (cache or __user_cache__).add(EventMeta, func)
        meta.set(func, EventMeta(event, priority))
        return func

    return decorator


def on_initialized[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_INITIALIZED_EVENT, cache=cache)


def on_started[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_STARTED_EVENT, cache=cache)


def on_stopped[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_STOPPED_EVENT, cache=cache)


def on_error[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_ERROR_EVENT, cache=cache)
