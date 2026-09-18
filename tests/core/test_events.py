"""Event listener decorators and the `EventDispatcher`."""

from typing import Any

import pytest
from escondite import Cache
from soupape import AsyncInjector, ServiceCollection

from bolinette.core import meta
from bolinette.core.events import (
    BLNT_ERROR_EVENT,
    BLNT_INITIALIZED_EVENT,
    BLNT_STARTED_EVENT,
    BLNT_STOPPED_EVENT,
    EventContext,
    EventDispatcher,
    on_error,
    on_event,
    on_initialized,
    on_started,
    on_stopped,
)
from bolinette.core.events._decorators import EventMeta


def _listeners(cache: Cache) -> list[Any]:
    return list(cache.get(EventMeta.KEY, raises=False))


def _event_meta(func: Any) -> EventMeta:
    return meta.get(func, EventMeta.KEY)


async def _dispatcher(cache: Cache, services: ServiceCollection | None = None) -> EventDispatcher:
    services = services if services is not None else ServiceCollection()
    services.add_singleton(Cache, lambda: cache)
    services.add_singleton(EventDispatcher)
    injector = AsyncInjector(services)
    await injector.__aenter__()
    return await injector.require(EventDispatcher)


class TestOnEventDecorator:
    def test_decorator_form(self, cache: Cache) -> None:
        """`on_event(name)` used as a decorator registers the function and its metadata."""

        @on_event("custom", cache=cache)
        async def listener() -> None:
            pass

        assert _listeners(cache) == [listener]
        assert _event_meta(listener) == EventMeta("custom", 1000)

    def test_direct_form(self, cache: Cache) -> None:
        """`on_event(func, name)` registers an existing function and returns it."""

        async def listener() -> None:
            pass

        assert on_event(listener, "custom", priority=5, cache=cache) is listener
        assert _event_meta(listener) == EventMeta("custom", 5)

    def test_invalid_arguments_raise(self, cache: Cache) -> None:
        """Any other argument shape is a programming error."""
        with pytest.raises(TypeError):
            on_event(cache=cache)  # pyright: ignore[reportCallIssue]

    def test_lifecycle_shortcuts(self, cache: Cache) -> None:
        """The lifecycle shortcuts register on their respective event names."""

        @on_initialized(cache=cache)
        async def initialized() -> None:
            pass

        @on_started(cache=cache)
        async def started() -> None:
            pass

        @on_stopped(cache=cache)
        async def stopped() -> None:
            pass

        @on_error(cache=cache)
        async def error() -> None:
            pass

        assert _event_meta(initialized).event == BLNT_INITIALIZED_EVENT
        assert _event_meta(started).event == BLNT_STARTED_EVENT
        assert _event_meta(stopped).event == BLNT_STOPPED_EVENT
        assert _event_meta(error).event == BLNT_ERROR_EVENT


class TestDispatcher:
    async def test_cached_listeners_are_loaded(self, cache: Cache) -> None:
        """Listeners found in the cache are called when their event is dispatched."""
        calls: list[str] = []

        @on_event("custom", cache=cache)
        async def listener() -> None:
            calls.append("called")

        dispatcher = await _dispatcher(cache)
        await dispatcher.dispatch("custom")

        assert calls == ["called"]

    async def test_other_events_are_not_triggered(self, cache: Cache) -> None:
        """Dispatching an event does not call listeners of other events."""
        calls: list[str] = []

        @on_event("custom", cache=cache)
        async def listener() -> None:
            calls.append("called")

        dispatcher = await _dispatcher(cache)
        await dispatcher.dispatch("other")

        assert calls == []

    async def test_unknown_event_is_a_no_op(self, cache: Cache) -> None:
        """Dispatching an event nobody listens to does nothing."""
        dispatcher = await _dispatcher(cache)

        await dispatcher.dispatch("nobody")

    async def test_priority_order(self, cache: Cache) -> None:
        """Listeners run in ascending priority order whatever their registration order."""
        calls: list[str] = []

        @on_event("custom", priority=30, cache=cache)
        async def third() -> None:
            calls.append("third")

        @on_event("custom", priority=10, cache=cache)
        async def first() -> None:
            calls.append("first")

        @on_event("custom", priority=20, cache=cache)
        async def second() -> None:
            calls.append("second")

        dispatcher = await _dispatcher(cache)
        await dispatcher.dispatch("custom")

        assert calls == ["first", "second", "third"]

    async def test_positional_and_named_arguments(self, cache: Cache) -> None:
        """Dispatch arguments are forwarded to the listener as positional and keyword arguments."""
        received: list[tuple[int, str]] = []

        @on_event("custom", cache=cache)
        async def listener(a: int, b: str) -> None:
            received.append((a, b))

        dispatcher = await _dispatcher(cache)
        await dispatcher.dispatch("custom", args=[1], kwargs={"b": "x"})

        assert received == [(1, "x")]

    async def test_services_are_injected(self, cache: Cache) -> None:
        """Listener parameters not given as arguments are resolved by the injector."""

        class Service:
            pass

        seen: list[Service] = []

        @on_event("custom", cache=cache)
        async def listener(service: Service) -> None:
            seen.append(service)

        services = ServiceCollection()
        services.add_singleton(Service)
        dispatcher = await _dispatcher(cache, services)
        await dispatcher.dispatch("custom")

        assert len(seen) == 1
        assert isinstance(seen[0], Service)

    async def test_event_context_is_injectable(self, cache: Cache) -> None:
        """A context given to `dispatch` is available to listeners as `EventContext`."""
        seen: list[int] = []

        @on_event("custom", cache=cache)
        async def listener(context: EventContext[int]) -> None:
            seen.append(context.value)

        dispatcher = await _dispatcher(cache)
        await dispatcher.dispatch("custom", context=EventContext(42))

        assert seen == [42]

    async def test_add_listener_at_runtime(self, cache: Cache) -> None:
        """Listeners can be added directly on the dispatcher, ordered by priority with the cached ones."""
        calls: list[str] = []

        @on_event("custom", priority=20, cache=cache)
        async def cached() -> None:
            calls.append("cached")

        async def runtime() -> None:
            calls.append("runtime")

        dispatcher = await _dispatcher(cache)
        dispatcher.add_listener("custom", runtime, priority=10)
        await dispatcher.dispatch("custom")

        assert calls == ["runtime", "cached"]
