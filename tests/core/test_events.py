from bolinette.core import Cache
from bolinette.core.events import EventDispatcher, on_event
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

    await dispatcher.dispatch("event1")
    await dispatcher.dispatch("event1")
    await dispatcher.dispatch("event2")

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

    dispatcher = mock.injection.require(EventDispatcher)

    await dispatcher.dispatch("event1")
    await dispatcher.dispatch("event1")
    await dispatcher.dispatch("event2")

    assert order == ["listener1", "listener1", "listener2"]


async def test_listener_priority() -> None:
    cache = Cache()

    mock = Mock(cache=cache)
    mock.injection.add_singleton(EventDispatcher)

    order1: list[str] = []
    order2: list[str] = []

    async def listener11() -> None:
        order1.append("listener11")

    async def listener12() -> None:
        order1.append("listener12")

    async def listener21() -> None:
        order2.append("listener21")

    async def listener22() -> None:
        order2.append("listener22")

    on_event("event1", cache=cache)(listener11)
    on_event("event1", cache=cache)(listener12)
    on_event("event2", 1, cache=cache)(listener21)
    on_event("event2", 0, cache=cache)(listener22)

    dispatcher = mock.injection.require(EventDispatcher)

    await dispatcher.dispatch("event1")
    assert order1 == ["listener11", "listener12"]

    await dispatcher.dispatch("event2")
    assert order2 == ["listener22", "listener21"]
