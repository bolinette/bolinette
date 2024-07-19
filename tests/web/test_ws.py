import json
from typing import Any, Literal

from bolinette.core import Cache, CoreSection
from bolinette.core.logging import Logger
from bolinette.core.testing import Mock
from bolinette.core.types import TypeChecker
from bolinette.web.ws import (
    ChannelMessage,
    WebSocketContext,
    WebSocketHandler,
    WebSocketSubResult,
    WebSocketSubscription,
    channel,
    topic,
)


class MockRequest:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def get_type(self) -> Literal["raw", "text"]:
        return "text"

    def raw(self) -> bytes:
        raise TypeError()

    def text(self) -> str:
        return self._payload

    def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any:
        return json.loads(self._payload, cls=cls)


class MockResponse:
    def __init__(self) -> None:
        self.queue: list[object] = []

    async def send(self, *args: Any, **kwargs: Any) -> Any:
        if "raw" in kwargs:
            self.queue.append(kwargs["raw"])
        if "text" in kwargs:
            self.queue.append(kwargs["text"])
        if "json" in kwargs:
            self.queue.append(kwargs["json"])


async def test_send_str_message() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebSocketHandler])
    mock.mock(CoreSection).setup(lambda c: c.debug, False)

    def mock_check(value: object, of_type: type[Any]) -> bool:
        return True

    mock.mock(TypeChecker).setup(lambda tc: tc.instanceof, mock_check)

    mock.injection.add_singleton(WebSocketHandler)

    class TestTopic:
        async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
            return sub.accept()

        @channel(".*")
        async def test_channel(self, message: ChannelMessage[str]) -> None:
            assert message.channel == "message"
            assert message.value == "hello"

    topic("test", cache=cache)(TestTopic)

    ws_handler = mock.injection.require(WebSocketHandler)

    await ws_handler.handle(
        MockRequest(json.dumps({"action": "send", "topic": "test", "channel": "message", "data": "hello"})),
        MockResponse(),
    )


async def test_fail_bad_message() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebSocketHandler]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, False)

    def mock_check(value: object, of_type: type[Any]) -> bool:
        return True

    mock.mock(TypeChecker).setup(lambda tc: tc.instanceof, mock_check)

    mock.injection.add_singleton(WebSocketHandler)

    class TestTopic:
        async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
            return sub.accept()

        @channel(".*")
        async def test_channel(self, message: ChannelMessage[str]) -> None:
            assert message.channel == "message"
            assert message.value == "hello"

    topic("test", cache=cache)(TestTopic)

    ws_handler = mock.injection.require(WebSocketHandler)

    response = MockResponse()
    await ws_handler.handle(MockRequest(json.dumps({})), response)

    assert len(response.queue) == 1
    resp_content = response.queue[0]
    assert isinstance(resp_content, dict)
    assert resp_content["status"] == 400
    assert resp_content["errors"][0] == {
        "code": "ws.bad_request",
        "message": "Invalid message, action must be sub, unsub, send or close",
        "params": {},
    }


async def test_subscribe_and_receiveand_unsub() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebSocketHandler]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, False)

    def mock_check(value: object, of_type: type[Any]) -> bool:
        return True

    mock.mock(TypeChecker).setup(lambda tc: tc.instanceof, mock_check)

    mock.injection.add_singleton(WebSocketHandler)

    class TestTopic:
        async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
            return sub.accept()

    topic("test", cache=cache)(TestTopic)

    ws_handler = mock.injection.require(WebSocketHandler)
    context = mock.injection.require(WebSocketContext)
    response = MockResponse()

    await ws_handler.handle(
        MockRequest(json.dumps({"action": "sub", "topic": "test", "channel": "user1"})),
        response,
    )
    await context.send("test", "user1", {"content": "text1"})
    assert response.queue == [{"content": "text1"}]
    await context.send("test", "user1", {"content": "text2"})
    assert response.queue == [{"content": "text1"}, {"content": "text2"}]

    await ws_handler.handle(
        MockRequest(json.dumps({"action": "unsub", "topic": "test", "channel": "user1"})),
        response,
    )
    await context.send("test", "user1", {"content": "text3"})
    assert response.queue == [{"content": "text1"}, {"content": "text2"}]
