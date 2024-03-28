from collections.abc import Awaitable, Callable
from typing import Any, Literal, NotRequired, TypedDict


class ASGIVersion(TypedDict):
    version: str
    spec_version: NotRequired[str]


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: ASGIVersion


class WebMessageScope(TypedDict):
    asgi: ASGIVersion
    http_version: Literal["1.0", "1.1", "2", "3"]
    server: NotRequired[tuple[str, int] | tuple[str, None]]
    client: NotRequired[tuple[str, int]]
    scheme: NotRequired[str]
    method: str
    root_path: NotRequired[str]
    path: str
    raw_path: NotRequired[bytes]
    query_string: bytes
    headers: list[tuple[bytes, bytes]]
    state: NotRequired[dict[str, Any]]


class HttpScope(WebMessageScope):
    type: Literal["http"]


class WebSocketScope(WebMessageScope):
    type: Literal["websocket"]
    subprotocols: NotRequired[list[str]]


class LifespanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]


class LifespanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]


class LifespanStartupComplete(TypedDict):
    type: Literal["lifespan.startup.complete"]


class LifespanStartupFailed(TypedDict):
    type: Literal["lifespan.startup.failed"]


class LifespanShutdownComplete(TypedDict):
    type: Literal["lifespan.shutdown.complete"]


class LifespanShutdownFailed(TypedDict):
    type: Literal["lifespan.shutdown.failed"]


class HttpRequestEvent(TypedDict):
    type: Literal["http.request"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class HttpDisconectEvent(TypedDict):
    type: Literal["http.disconnect"]


class HttpResponseStart(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[list[tuple[bytes, bytes]]]
    trailers: NotRequired[bool]


class HttpResponseBody(TypedDict):
    type: Literal["http.response.body"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class WebSocketConnectEvent(TypedDict):
    type: Literal["websocket.connect"]


class WebSocketReceiveBytesEvent(TypedDict):
    type: Literal["websocket.receive"]
    bytes: bytes
    text: NotRequired[None]


class WebSocketReceiveTextEvent(TypedDict):
    type: Literal["websocket.receive"]
    bytes: NotRequired[None]
    text: str


class WebSocketDisconnectEvent(TypedDict):
    type: Literal["websocket.disconnect"]
    code: int


class WebSocketAcceptResult(TypedDict):
    type: Literal["websocket.accept"]
    subprotocol: NotRequired[str]
    headers: NotRequired[list[tuple[bytes, bytes]]]


class WebSocketSendBytesResult(TypedDict):
    type: Literal["websocket.send"]
    bytes: bytes
    text: NotRequired[None]


class WebSocketSendTextResult(TypedDict):
    type: Literal["websocket.send"]
    bytes: NotRequired[None]
    text: str


class WebSocketCloseResult(TypedDict):
    type: Literal["websocket.close"]
    code: NotRequired[int]
    reason: NotRequired[str | None]


type Scope = LifespanScope | HttpScope | WebSocketScope

type LifespanReceivedEvent = LifespanStartupEvent | LifespanShutdownEvent
type LifespanStartupResult = LifespanStartupComplete | LifespanStartupFailed
type LifespanShutdownResult = LifespanShutdownComplete | LifespanShutdownFailed
type LifespanResult = LifespanStartupResult | LifespanShutdownResult

type HttpReceivedEvent = HttpRequestEvent | HttpDisconectEvent
type HttpResponseResult = HttpResponseStart | HttpResponseBody

type WebSocketReceivedEvent = (
    WebSocketConnectEvent | WebSocketReceiveBytesEvent | WebSocketReceiveTextEvent | WebSocketDisconnectEvent
)
type WebSocketConnectResult = WebSocketAcceptResult | WebSocketCloseResult
type WebSocketSendResult = WebSocketSendBytesResult | WebSocketSendTextResult
type WebSocketResult = WebSocketConnectResult | WebSocketSendResult

type AsgiCallable = Callable[[Scope, Callable[[], Awaitable[Any]], Callable[[Any], Awaitable[None]]], Awaitable[Any]]
