from collections.abc import Awaitable, Callable
from typing import Any, Literal, NotRequired, TypedDict


class ASGIVersion(TypedDict):
    version: str
    spec_version: NotRequired[str]


class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: ASGIVersion


class HttpScope(TypedDict):
    type: Literal["http"]
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


type Scope = LifespanScope | HttpScope


class LifespanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]


class LifespanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]


type LifespanReceivedEvent = LifespanStartupEvent | LifespanShutdownEvent


class LifespanStartupComplete(TypedDict):
    type: Literal["lifespan.startup.complete"]


class LifespanStartupFailed(TypedDict):
    type: Literal["lifespan.startup.failed"]


class LifespanShutdownComplete(TypedDict):
    type: Literal["lifespan.shutdown.complete"]


class LifespanShutdownFailed(TypedDict):
    type: Literal["lifespan.shutdown.failed"]


type LifespanStartupResult = LifespanStartupComplete | LifespanStartupFailed
type LifespanShutdownResult = LifespanShutdownComplete | LifespanShutdownFailed
type LifespanResult = LifespanStartupResult | LifespanShutdownResult


class HttpRequestEvent(TypedDict):
    type: Literal["http.request"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


class HttpDisconectEvent(TypedDict):
    type: Literal["http.disconnect"]


type HttpReceivedEvent = HttpRequestEvent | HttpDisconectEvent


class HttpResponseStart(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[list[tuple[bytes, bytes]]]
    trailers: NotRequired[bool]


class HttpResponseBody(TypedDict):
    type: Literal["http.response.body"]
    body: NotRequired[bytes]
    more_body: NotRequired[bool]


type HttpResponseResult = HttpResponseStart | HttpResponseBody

type AsgiCallable = Callable[[Scope, Callable[[], Awaitable[Any]], Callable[[Any], Awaitable[None]]], Awaitable[Any]]
