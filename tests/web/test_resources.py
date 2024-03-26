import json
from collections.abc import AsyncGenerator, Callable, Coroutine, Generator
from dataclasses import dataclass
from http import HTTPStatus
from io import BytesIO
from typing import Annotated, Any

from bolinette.core import Cache, Logger
from bolinette.core.environment import CoreSection
from bolinette.core.mapping import Mapper
from bolinette.core.testing import Mock
from bolinette.core.types import TypeChecker
from bolinette.web import Payload, controller, delete, get, patch, post, put
from bolinette.web.abstract import ResponseState
from bolinette.web.config import WebConfig
from bolinette.web.resources import HttpHeaders, ResponseData, WebResources


class MockRequest:
    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, str] | None = None,
        path_params: dict[str, str] | None = None,
        payload: bytes | None = None,
    ):
        self.method = method
        self.path = path
        self.headers = headers or {}
        self.query_params = query_params or {}
        self.path_params = path_params or {}
        self._payload = payload

    async def raw(self) -> bytes:
        return self._payload or b""

    async def text(self, *, encoding: str = "utf-8") -> str:
        return "" if self._payload is None else self._payload.decode(encoding)

    async def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any:
        return None if self._payload is None else json.loads(self._payload, cls=cls)


class MockResponse:
    def __init__(self, buffer: BytesIO | None = None) -> None:
        self.buffer = buffer
        self._headers: dict[str, str] = {}
        self._status: int = 200
        self._state: ResponseState = ResponseState.Idle

    @property
    def status(self) -> int:
        return self._status

    @property
    def headers(self) -> dict[str, str]:
        return {**self._headers}

    @property
    def state(self) -> ResponseState:
        return self._state

    async def open(self) -> None:
        self._state = ResponseState.Started

    async def close(self) -> None:
        self._state = ResponseState.Closed

    async def write(self, raw: bytes) -> None:
        if self.buffer:
            self.buffer.write(raw)
        self._state = ResponseState.Sending

    def set_status(self, status: int, /) -> None:
        self._status = status

    def set_header(self, key: str, value: str, /) -> None:
        self._headers[key] = value

    def has_header(self, key: str, /) -> bool:
        return key in self._headers

    def unset_header(self, key: str, /) -> None:
        del self._headers[key]


async def test_call_route_returns_str() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get("")
        async def test_route(self) -> str:
            return "test"

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    resources = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    resp = MockResponse(buffer)
    await resources.dispatch(MockRequest("GET", "/"), resp)

    buffer.seek(0)
    assert buffer.read() == b"test"
    assert resp.status == 200
    assert resp.headers[HttpHeaders.ContentType] == "text/plain"


async def test_call_route_returns_int() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get("")
        async def test_route(self) -> int:
            return 1

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    resources = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    resp = MockResponse(buffer)
    await resources.dispatch(MockRequest("GET", "/"), resp)

    buffer.seek(0)
    assert buffer.read() == b"1"
    assert resp.headers[HttpHeaders.ContentType] == "application/json"


async def test_call_route_returns_bytes() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get("")
        async def test_route(self) -> bytes:
            return b"test"

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    resources = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    resp = MockResponse(buffer)
    await resources.dispatch(MockRequest("GET", "/"), resp)

    buffer.seek(0)
    assert buffer.read() == b"test"
    assert resp.headers[HttpHeaders.ContentType] == "application/octet-stream"


async def test_call_route_int_param() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"{id}")
        async def test_route(self, id: int) -> int:
            return id + 1

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    await res.dispatch(MockRequest("GET", "/1"), MockResponse(buffer))

    buffer.seek(0)
    assert buffer.read() == b"2"


async def test_call_route_int_asyncgenerator() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"")
        async def test_route(self) -> AsyncGenerator[int, None]:
            yield 1
            yield 2
            yield 3

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    await res.dispatch(MockRequest("GET", "/"), MockResponse(buffer))

    buffer.seek(0)
    assert buffer.read() == b"[1, 2, 3]"


async def test_call_route_int_generator() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"")
        def test_route(self) -> Generator[int, None, None]:
            yield 1
            yield 2
            yield 3

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    await res.dispatch(MockRequest("GET", "/"), MockResponse(buffer))

    buffer.seek(0)
    assert buffer.read() == b"[1, 2, 3]"


async def test_call_route_returns_coroutine() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"")
        def test_route(self) -> Callable[[], Coroutine[Any, Any, list[int]]]:
            async def route() -> list[int]:
                return [1, 2, 3]

            return route

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    await res.dispatch(MockRequest("GET", "/"), MockResponse(buffer))

    buffer.seek(0)
    assert buffer.read() == b"[1, 2, 3]"


async def test_call_route_returns_asyncgen() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"")
        def test_route(self) -> Callable[[], AsyncGenerator[int, None]]:
            async def route() -> AsyncGenerator[int, None]:
                yield 1
                yield 2
                yield 3

            return route

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    await res.dispatch(MockRequest("GET", "/"), MockResponse(buffer))

    buffer.seek(0)
    assert buffer.read() == b"[1, 2, 3]"


async def test_fail_route_not_found() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller: ...

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    response = MockResponse(buffer)
    await res.dispatch(MockRequest("GET", "/"), response)

    buffer.seek(0)
    assert buffer.read() == b"404 Not Found"
    assert response.status == 404


async def test_fail_route_method_not_allowed() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).dummy()
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"")
        def test_route(self) -> None: ...

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    response = MockResponse(buffer)
    await res.dispatch(MockRequest("POST", "/"), response)

    buffer.seek(0)
    assert buffer.read() == b"405 Method Not Allowed"
    assert response.status == 405


async def test_fail_route_raises_exception() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, False)
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get(r"")
        def test_route(self) -> None:
            raise Exception()

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    response = MockResponse(buffer)
    await res.dispatch(MockRequest("GET", "/"), response)

    buffer.seek(0)
    assert json.loads(buffer.read()) == {
        "status": 500,
        "reason": "Internal Server Error",
        "errors": [
            {
                "message": "Un unexpected error has occured while processing the request",
                "code": "internal.error",
                "params": {},
            }
        ],
    }
    assert response.status == 500


async def test_fail_route_raises_exception_debug() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, True)
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class CustomError(Exception): ...

    class Controller:
        @get(r"")
        def test_route(self) -> None:
            raise CustomError("An error has been encountered :(")

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    response = MockResponse(buffer)
    await res.dispatch(MockRequest("GET", "/"), response)

    buffer.seek(0)
    message = json.loads(buffer.read())
    assert message["status"] == 500
    assert message["reason"] == "Internal Server Error"
    assert message["errors"] == [
        {
            "message": "Un unexpected error has occured while processing the request",
            "code": "internal.error",
            "params": {},
        }
    ]
    assert message["debug"]["message"] == "An error has been encountered :("
    assert message["debug"]["type"] == str(CustomError)
    assert len(message["debug"]["stacktrace"]) > 0

    assert response.status == 500


async def test_call_many_routes() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, True)
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    order: list[str] = []

    class Controller:
        @get("entity/get")
        def route_1(self) -> None:
            order.append("1")

        @post("entity/post")
        def route_2(self) -> None:
            order.append("2")

        @put("entity/put")
        def route_3(self) -> None:
            order.append("3")

        @patch("entity/patch")
        def route_4(self) -> None:
            order.append("4")

        @delete("entity/delete")
        def route_5(self) -> None:
            order.append("5")

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)

    await res.dispatch(MockRequest("GET", "/entity/get"), MockResponse())
    await res.dispatch(MockRequest("POST", "/entity/post"), MockResponse())
    await res.dispatch(MockRequest("PUT", "/entity/put"), MockResponse())
    await res.dispatch(MockRequest("PATCH", "/entity/patch"), MockResponse())
    await res.dispatch(MockRequest("DELETE", "/entity/delete"), MockResponse())

    assert order == ["1", "2", "3", "4", "5"]


async def test_call_route_with_class_payload() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, True)
    mock.mock(TypeChecker).dummy()
    mock.mock(WebConfig).dummy()

    @dataclass()
    class TestPayload:
        name: str
        quantity: int

    class Controller:
        @post("")
        def route_1(self, payload: Annotated[TestPayload, Payload]) -> str:
            assert isinstance(payload, TestPayload)
            return f"Ordered {payload.quantity} of {payload.name}."

    controller("/", cache=cache)(Controller)

    def mock_map(
        src_cls: type[dict[str, Any]],
        dest_cls: type[TestPayload],
        src: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> TestPayload:
        return dest_cls(**src)

    mock.mock(Mapper).setup(lambda m: m.map, mock_map)

    mock.injection.add(WebResources, strategy="singleton")
    res = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    payload = json.dumps({"name": "Item", "quantity": 2}).encode()
    response = MockResponse(buffer)
    await res.dispatch(MockRequest("POST", "/", payload=payload), response)

    buffer.seek(0)
    message = buffer.read()
    assert message == b"Ordered 2 of Item."
    assert response.status == 200


async def test_set_response_status() -> None:
    cache = Cache()
    mock = Mock(cache=cache)
    mock.mock(Logger[WebResources]).dummy()
    mock.mock(CoreSection).setup(lambda c: c.debug, True)
    mock.mock(TypeChecker).dummy()
    mock.mock(Mapper).dummy()
    mock.mock(WebConfig).dummy()

    class Controller:
        @get("")
        async def test_route(self, response: ResponseData) -> str:
            response.set_status(HTTPStatus.CREATED)
            return "test"

    controller("/", cache=cache)(Controller)

    mock.injection.add(WebResources, strategy="singleton")
    resources = mock.injection.instantiate(WebResources)
    buffer = BytesIO()

    resp = MockResponse(buffer)
    await resources.dispatch(MockRequest("GET", "/"), resp)

    buffer.seek(0)
    assert buffer.read() == b"test"
    assert resp.status == 201
    assert resp.headers[HttpHeaders.ContentType] == "text/plain"
