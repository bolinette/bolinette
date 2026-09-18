import json
from typing import Any

import pytest
from escondite import Cache
from peritype import wrap_type

from bolinette.core import meta
from bolinette.web import AsgiApplication
from bolinette.web._abstract import WebSocketResponse
from bolinette.web.exceptions import NotFoundError
from bolinette.web.ws import (
    ChannelMessage,
    WebSocketContext,
    WebSocketSubResult,
    WebSocketSubscription,
    channel,
    topic,
)
from bolinette.web.ws._channel import WebSocketChannelMeta
from bolinette.web.ws._handler import WebSocketHandler, _WSTypeBag  # pyright: ignore[reportPrivateUsage]
from bolinette.web.ws._topic import WebSocketTopicMeta
from tests.web.conftest import AppFactory, AsgiClient, ws_message


class _Socket:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    async def send(self, **kwargs: Any) -> None:
        self.sent.append(kwargs)


def _errors(sent: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [json.loads(m["text"]) for m in sent if m["type"] == "websocket.send"]


async def _client(make_app: AppFactory) -> AsgiClient:
    blnt = await make_app()
    return AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())


def _rooms_topic(cache: Cache) -> type[Any]:
    @topic("rooms", cache=cache)
    class Rooms:
        async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
            if sub.channel == "secret":
                return sub.reject()
            return sub.accept()

        @channel(r"room-\d+")
        async def on_room(self, message: ChannelMessage[Any], context: WebSocketContext) -> None:
            await context.send("rooms", message.channel, {"echo": message.value})

    return Rooms


class TestSubscription:
    def test_accept_and_reject(self) -> None:
        sub = WebSocketSubscription("a")

        assert sub.channel == "a"
        assert bool(sub.accept()) is True
        assert bool(sub.reject()) is False
        assert bool(WebSocketSubResult(True)) is True


class TestDecorators:
    def test_topic_registers_the_class(self, cache: Cache) -> None:
        rooms_cls = _rooms_topic(cache)

        assert list(cache.get(WebSocketTopicMeta.KEY, raises=False)) == [rooms_cls]
        topic_meta: WebSocketTopicMeta = meta.get(rooms_cls, WebSocketTopicMeta.KEY)
        assert topic_meta.name == "rooms"

    def test_channel_sets_its_metadata(self, cache: Cache) -> None:
        rooms_cls = _rooms_topic(cache)
        chan_meta: WebSocketChannelMeta[Any, Any, ..., Any] = meta.get(rooms_cls.on_room, WebSocketChannelMeta.KEY)

        assert chan_meta.pattern.pattern == r"room-\d+"
        assert chan_meta.func is rooms_cls.on_room

    def test_channel_message_keeps_the_value_type(self) -> None:
        socket = _Socket()
        message = ChannelMessage("room-1", 3, socket)

        assert (message.channel, message.value, message.type) == ("room-1", 3, int)
        assert message.response is socket


class TestHandlerMessages:
    async def test_subscribe_then_send_reaches_the_subscriber(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "sub", "topic": "rooms", "channel": "room-1"}),
            ws_message({"action": "send", "topic": "rooms", "channel": "room-1", "data": {"hello": "world"}}),
        )

        assert _errors(sent) == [{"echo": {"hello": "world"}}]

    async def test_a_rejected_subscription_is_forbidden(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "sub", "topic": "rooms", "channel": "secret"}),
        )

        payload = _errors(sent)[0]
        assert payload["status"] == 403
        assert payload["errors"][0]["code"] == "ws.subscription.rejected"

    async def test_an_unknown_topic_is_not_found(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "sub", "topic": "ghost", "channel": "room-1"}),
        )

        assert _errors(sent)[0]["errors"][0]["code"] == "ws.topic.not_found"

    async def test_unsubscribe_removes_the_subscription(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "sub", "topic": "rooms", "channel": "room-1"}),
            ws_message({"action": "unsub", "topic": "rooms", "channel": "room-1"}),
            ws_message({"action": "send", "topic": "rooms", "channel": "room-1", "data": 1}),
        )

        assert _errors(sent) == []

    async def test_unsubscribing_twice_is_not_found(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "unsub", "topic": "rooms", "channel": "room-1"}),
        )

        assert _errors(sent)[0]["errors"][0]["code"] == "ws.subscription.not_found"

    async def test_sending_on_an_unmatched_channel_does_nothing(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "send", "topic": "rooms", "channel": "lobby", "data": 1}),
        )

        assert _errors(sent) == []

    async def test_close_drops_every_subscription(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "sub", "topic": "rooms", "channel": "room-1"}),
            ws_message({"action": "close"}),
            ws_message({"action": "send", "topic": "rooms", "channel": "room-1", "data": 1}),
        )

        assert _errors(sent) == []

    @pytest.mark.parametrize(
        "payload",
        [
            {"action": "nope"},
            {"topic": "rooms"},
            {"action": "sub", "topic": "rooms"},
            {"action": "unsub", "channel": "room-1"},
            {"action": "send", "topic": "rooms", "channel": "room-1"},
        ],
    )
    async def test_malformed_messages_are_bad_requests(
        self, make_app: AppFactory, cache: Cache, payload: dict[str, Any]
    ) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket({"type": "websocket.connect"}, ws_message(payload))

        assert _errors(sent)[0]["errors"][0]["code"] == "ws.bad_request"

    async def test_a_non_object_message_is_a_bad_request(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)

        sent = await client.websocket({"type": "websocket.connect"}, {"type": "websocket.receive", "text": "[]"})

        assert _errors(sent)[0]["errors"][0]["code"] == "ws.bad_request"

    async def test_raw_messages_are_parsed(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        client = await _client(make_app)
        payload = json.dumps({"action": "sub", "topic": "ghost", "channel": "x"}).encode()

        sent = await client.websocket(
            {"type": "websocket.connect"},
            {"type": "websocket.receive", "bytes": payload},
        )

        assert _errors(sent)[0]["errors"][0]["code"] == "ws.topic.not_found"


class TestWebSocketContext:
    async def test_send_to_several_subscribers(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        blnt = await make_app()
        handler = await blnt.injector.require(WebSocketHandler)
        context = await blnt.injector.require(WebSocketContext)
        first, second = _Socket(), _Socket()
        handler.topics["rooms"].add_subscription("room-1", first)
        handler.topics["rooms"].add_subscription("room-1", second)

        await context.send("rooms", "room-1", {"a": 1})

        assert first.sent == [{"json": {"a": 1}}]
        assert second.sent == [{"json": {"a": 1}}]

    async def test_send_to_an_unknown_topic_is_ignored(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        blnt = await make_app()
        context = await blnt.injector.require(WebSocketContext)

        await context.send("ghost", "room-1", 1)

    async def test_send_to_an_unknown_channel_is_ignored(self, make_app: AppFactory, cache: Cache) -> None:
        _rooms_topic(cache)
        blnt = await make_app()
        context = await blnt.injector.require(WebSocketContext)

        await context.send("rooms", "room-9", 1)


class TestTypeBag:
    def test_subscription_bookkeeping(self, cache: Cache) -> None:
        bag = _WSTypeBag(wrap_type(_rooms_topic(cache)))
        socket: WebSocketResponse = _Socket()

        bag.add_subscription("room-1", socket)
        bag.add_subscription("room-1", _Socket())

        assert bag.is_registered("room-1", socket)
        bag.remove_subscription("room-1", socket)
        assert not bag.is_registered("room-1", socket)

    def test_removing_an_unknown_channel_raises(self, cache: Cache) -> None:
        bag = _WSTypeBag(wrap_type(_rooms_topic(cache)))

        with pytest.raises(NotFoundError) as raised:
            bag.remove_subscription("room-1", _Socket())

        assert raised.value.error_code == "ws.subscription.not_found"

    def test_removing_an_unknown_socket_raises(self, cache: Cache) -> None:
        bag = _WSTypeBag(wrap_type(_rooms_topic(cache)))
        bag.add_subscription("room-1", _Socket())

        with pytest.raises(NotFoundError):
            bag.remove_subscription("room-1", _Socket())

    def test_match_returns_none_without_a_channel(self, cache: Cache) -> None:
        @topic("plain", cache=cache)
        class Plain:
            async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
                return sub.accept()

        assert _WSTypeBag(wrap_type(Plain)).match("anything") is None


class TestHandlerInternals:
    async def test_an_awaitable_channel_result_is_awaited(self, make_app: AppFactory, cache: Cache) -> None:
        seen: list[str] = []

        async def later() -> None:
            seen.append("awaited")

        @topic("lazy", cache=cache)
        class Lazy:
            async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
                return sub.accept()

            @channel("c")
            def on_c(self, message: ChannelMessage[Any]) -> Any:
                return later()

        client = await _client(make_app)
        await client.websocket(
            {"type": "websocket.connect"},
            ws_message({"action": "send", "topic": "lazy", "channel": "c", "data": 1}),
        )

        assert seen == ["awaited"]

    async def test_a_subscription_missing_from_the_handler_is_not_found(
        self, make_app: AppFactory, cache: Cache
    ) -> None:
        _rooms_topic(cache)
        blnt = await make_app()
        handler = await blnt.injector.require(WebSocketHandler)

        with pytest.raises(NotFoundError) as raised:
            handler._remove_subscription(_Socket(), "rooms", "room-1")  # pyright: ignore[reportPrivateUsage]

        assert raised.value.error_args == {"topic": "rooms", "channel": "room-1"}
