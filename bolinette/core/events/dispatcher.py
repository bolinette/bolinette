from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from bolinette.core import Cache, meta
from bolinette.core.events import Event, EventListener
from bolinette.core.events.decorators import EventMeta
from bolinette.core.injection import post_init


class EventDispatcher:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Any]] = defaultdict(list)

    @post_init
    def _init_listeners(self, cache: Cache) -> None:
        for listener in cache.get(EventMeta, raises=False):
            event_meta = meta.get(listener, EventMeta)
            self.add_listener(event_meta.event, listener)

    def add_listener(self, event: Event | str, listener: EventListener) -> None:
        self._listeners[event].append(listener)

    async def dispatch(self, event: Event | str, callback: Callable[[EventListener], Awaitable[None]]) -> None:
        for listener in self._listeners[event]:
            await callback(listener)
