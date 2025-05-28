from collections import defaultdict
from dataclasses import dataclass

from bolinette.core import Cache, meta
from bolinette.core.events import EventListener
from bolinette.core.events.decorators import EventMeta
from bolinette.core.injection import Injection, post_init


@dataclass
class RegisteredEventListener:
    event: str
    priority: int
    callback: EventListener


class EventDispatcher:
    def __init__(self, inject: Injection) -> None:
        self._inject = inject
        self._listeners: dict[str, list[RegisteredEventListener]] = defaultdict(list)

    @post_init
    def _init_listeners(self, cache: Cache) -> None:
        for listener in cache.get(EventMeta, raises=False):
            event_meta = meta.get(listener, EventMeta)
            self.add_listener(event_meta.event, listener, event_meta.priority)

    def add_listener(self, event: str, listener: EventListener, priority: int = 0) -> None:
        self._listeners[event].append(RegisteredEventListener(event, priority, listener))

    async def dispatch(
        self,
        event: str,
        *,
        session: Injection | None = None,
        cache: Cache | None = None,
    ) -> None:
        if cache is not None:
            listeners: list[RegisteredEventListener] = []
            for listener in cache.get(EventMeta, raises=False):
                event_meta = meta.get(listener, EventMeta)
                if event_meta.event == event:
                    listeners.append(RegisteredEventListener(event_meta.event, event_meta.priority, listener))
        else:
            listeners = self._listeners.get(event, [])
        for listener in sorted(listeners, key=lambda listener: listener.priority):
            await (session or self._inject).call(listener.callback)
