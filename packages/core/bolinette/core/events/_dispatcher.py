from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from escondite import Cache
from soupape import AsyncInjector, post_init

from bolinette.core import meta
from bolinette.core.events import EventContext, EventListener
from bolinette.core.events._decorators import EventMeta


@dataclass(slots=True, frozen=True)
class RegisteredEventListener:
    event: str
    callback: EventListener
    priority: int


class EventDispatcher:
    def __init__(self, injector: AsyncInjector) -> None:
        self._injector = injector
        self._listeners: dict[str, list[RegisteredEventListener]] = defaultdict(list)

    @post_init
    def _init_listeners(self, cache: Cache) -> None:
        for listener in cache.get(EventMeta.KEY, raises=False):
            event_meta: EventMeta = meta.get(listener, EventMeta.KEY)
            self.add_listener(event_meta.event, listener, event_meta.priority)

    def add_listener(self, event: str, listener: EventListener, priority: int = 1000) -> None:
        self._listeners[event].append(RegisteredEventListener(event, listener, priority))

    async def dispatch(
        self,
        event: str,
        /,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        *,
        context: EventContext[Any] | None = None,
    ) -> None:
        listeners = self._listeners.get(event, [])
        for listener in sorted(listeners, key=lambda listener: listener.priority):
            async with self._injector.get_scoped_injector() as scoped_injector:
                if context is not None:
                    scoped_injector.services.add_scoped(EventContext, lambda: context)
                await scoped_injector.call(listener.callback, positional_args=args, named_args=kwargs)
