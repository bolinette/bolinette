from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, overload

from escondite import Cache

from bolinette.core import meta
from bolinette.core.events import (
    BLNT_ERROR_EVENT,
    BLNT_INITIALIZED_EVENT,
    BLNT_STARTED_EVENT,
    BLNT_STOPPED_EVENT,
    EventListener,
)


@dataclass(slots=True, frozen=True)
class EventMeta:
    KEY: ClassVar[str] = "__bltn_event_meta__"

    event: str
    priority: int


@overload
def on_event[FuncT: EventListener](
    func: FuncT,
    event: str,
    /,
    *,
    priority: int = 1000,
    cache: Cache | None = None,
) -> FuncT: ...
@overload
def on_event[FuncT: EventListener](
    event: str,
    /,
    *,
    priority: int = 1000,
    cache: Cache | None = None,
) -> Callable[[FuncT], FuncT]: ...
def on_event[FuncT: EventListener](
    *args: Any,
    priority: int = 1000,
    cache: Cache | None = None,
) -> Any:
    match args:
        case (func, str() as event):
            pass
        case (str() as event,):
            func = None
        case _:
            raise TypeError(*args)

    def decorator(func: FuncT) -> FuncT:
        Cache.with_fallback(cache).add(EventMeta.KEY, func)
        meta.set(func, EventMeta.KEY, EventMeta(event, priority))
        return func

    if func is not None:
        return decorator(func)
    return decorator


def on_initialized[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_INITIALIZED_EVENT, cache=cache)


def on_started[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_STARTED_EVENT, cache=cache)


def on_stopped[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_STOPPED_EVENT, cache=cache)


def on_error[FuncT: EventListener](*, cache: Cache | None = None) -> Callable[[FuncT], FuncT]:
    return on_event(BLNT_ERROR_EVENT, cache=cache)
