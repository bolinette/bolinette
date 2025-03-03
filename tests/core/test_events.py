from bolinette.core import Cache
from bolinette.core.events import EventDispatcher, EventListener, on_event
from bolinette.core.testing import Mock


async def test_event_dispatching() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add_singleton(EventDispatcher)

    dispatcher = mock.injection.require(EventDispatcher)

    order: list[str] = []

    async def listener1() -> None:
        order.append("listener1")

    async def listener2() -> None:
        order.append("listener2")

    dispatcher.add_listener("event1", listener1)
    dispatcher.add_listener("event2", listener2)

    async def callback(listener: EventListener) -> None:
        await listener()

    await dispatcher.dispatch("event1", callback)
    await dispatcher.dispatch("event1", callback)
    await dispatcher.dispatch("event2", callback)

    assert order == ["listener1", "listener1", "listener2"]


async def test_listener_from_decorator() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add_singleton(EventDispatcher)

    order: list[str] = []

    async def listener1() -> None:
        order.append("listener1")

    async def listener2() -> None:
        order.append("listener2")

    on_event("event1", cache=cache)(listener1)
    on_event("event2", cache=cache)(listener2)

    async def callback(listener: EventListener) -> None:
        await listener()

    dispatcher = mock.injection.require(EventDispatcher)

    await dispatcher.dispatch("event1", callback)
    await dispatcher.dispatch("event1", callback)
    await dispatcher.dispatch("event2", callback)

    assert order == ["listener1", "listener1", "listener2"]
