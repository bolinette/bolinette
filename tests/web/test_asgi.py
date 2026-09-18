import json
from typing import Any, cast

import pytest
from escondite import Cache

from bolinette.core import Bolinette, make_bolinette, startup
from bolinette.core.events import BLNT_STOPPED_EVENT, EventContext, on_event
from bolinette.web import (
    WEB_HTTP_INITIALIZED_EVENT,
    WEB_SERVER_STARTUP_COMPLETE_EVENT,
    WEB_SERVER_STARTUP_FAILED_EVENT,
    WEB_WS_INITIALIZED_EVENT,
    AsgiApplication,
    Controller,
    ResponseState,
    WebExtension,
    controller,
    create_asgi_app,
    get,
)
from bolinette.web._asgi import (
    AsgiRequest,
    AsgiResponse,
    AsgiSocketRequest,
    AsgiSocketResponse,
    HttpRequestEvent,
    Scope,
)
from bolinette.web.exceptions import InternalServerError
from tests.web.conftest import AppFactory, AsgiClient


async def _receive_nothing() -> Any:  # pragma: no cover
    raise AssertionError("receive should not be called")


def _collector() -> tuple[list[Any], Any]:
    sent: list[Any] = []

    async def send(message: Any) -> None:
        sent.append(message)

    return sent, send


class TestAsgiRequest:
    async def test_headers_are_lower_cased(self, make_app: AppFactory, cache: Cache) -> None:
        from bolinette.web import Request

        @controller("h", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, request: Request) -> str:
                return request.get_header("x-custom")

        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        assert (await client.request("GET", "/h", headers=[(b"X-Custom", b"v")])).text == "v"

    async def test_body_helpers(self) -> None:
        first: HttpRequestEvent = {"type": "http.request", "body": b'{"a":', "more_body": True}

        async def receive() -> Any:
            return {"type": "http.request", "body": b" 1}", "more_body": False}

        request = AsgiRequest("POST", "/x", {"Accept": "json"}, {}, first, receive)

        assert await request.json() == {"a": 1}

    async def test_raw_and_text(self) -> None:
        request = AsgiRequest("POST", "/x", {}, {}, {"type": "http.request", "body": b"hello"}, _receive_nothing)

        assert await request.raw() == b"hello"
        assert await request.text() == "hello"

    def test_header_access(self) -> None:
        request = AsgiRequest("GET", "/x", {"Accept": "json"}, {}, {"type": "http.request"}, _receive_nothing)

        assert request.headers == {"accept": "json"}
        assert request.has_header("ACCEPT")
        assert request.get_header("Accept") == "json"
        assert not request.has_header("missing")

    async def test_query_params_are_parsed(self, make_app: AppFactory, cache: Cache) -> None:
        from typing import Annotated

        from bolinette.web import QueryParam

        @controller("q", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self, a: Annotated[list[str], QueryParam()]) -> str:
                return "|".join(a)

        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        assert (await client.request("GET", "/q", query="a=1&a=&a=3")).text == "1||3"


class TestAsgiResponse:
    async def test_state_machine(self) -> None:
        sent, send = _collector()
        response = AsgiResponse(send)

        assert response.state is ResponseState.Idle
        response.set_status(201)
        response.set_header("x", "1")
        await response.open()
        assert response.state is ResponseState.Started
        await response.write(b"a")
        assert response.state is ResponseState.Sending
        await response.write(b"b")
        await response.close()

        assert response.state is ResponseState.Closed
        assert response.status == 201
        assert response.headers == {"x": "1"}
        assert sent[0] == {"type": "http.response.start", "status": 201, "headers": [(b"x", b"1")]}
        assert [m.get("body") for m in sent[1:]] == [b"a", b"b", b""]

    def test_headers_are_a_copy(self) -> None:
        _, send = _collector()
        response = AsgiResponse(send)

        response.set_header("x", "1")
        response.headers["y"] = "2"

        assert response.headers == {"x": "1"}

    def test_unset_header(self) -> None:
        _, send = _collector()
        response = AsgiResponse(send)

        response.set_header("x", "1")
        assert response.has_header("x")
        response.unset_header("x")
        response.unset_header("missing")

        assert not response.has_header("x")

    async def test_opening_twice_raises(self) -> None:
        _, send = _collector()
        response = AsgiResponse(send)
        await response.open()

        with pytest.raises(InternalServerError) as raised:
            await response.open()
        assert raised.value.message == "Response already started"

    async def test_closing_before_opening_raises(self) -> None:
        _, send = _collector()

        with pytest.raises(InternalServerError) as raised:
            await AsgiResponse(send).close()
        assert raised.value.message == "Response has not started"

    async def test_closing_twice_raises(self) -> None:
        _, send = _collector()
        response = AsgiResponse(send)
        await response.open()
        await response.close()

        with pytest.raises(InternalServerError) as raised:
            await response.close()
        assert raised.value.message == "Response has been closed"

    async def test_writing_before_opening_raises(self) -> None:
        _, send = _collector()

        with pytest.raises(InternalServerError) as raised:
            await AsgiResponse(send).write(b"a")
        assert raised.value.message == "Response has not started"

    async def test_writing_after_closing_raises(self) -> None:
        _, send = _collector()
        response = AsgiResponse(send)
        await response.open()
        await response.close()

        with pytest.raises(InternalServerError) as raised:
            await response.write(b"a")
        assert raised.value.message == "Response has been closed"


class TestAsgiSocketMessages:
    def test_raw_request(self) -> None:
        request = AsgiSocketRequest(b'{"a": 1}', None)

        assert request.get_type() == "raw"
        assert request.raw() == b'{"a": 1}'
        assert request.json() == {"a": 1}

    def test_text_request(self) -> None:
        request = AsgiSocketRequest(None, '{"a": 1}')

        assert request.get_type() == "text"
        assert request.text() == '{"a": 1}'
        assert request.json() == {"a": 1}

    def test_raw_on_a_text_request_raises(self) -> None:
        with pytest.raises(TypeError, match="unicode content"):
            AsgiSocketRequest(None, "x").raw()

    def test_text_on_a_raw_request_raises(self) -> None:
        with pytest.raises(TypeError, match="raw content"):
            AsgiSocketRequest(b"x", None).text()

    def test_json_without_any_content(self) -> None:
        assert AsgiSocketRequest(None, None).json() is None

    async def test_socket_response_sends_every_kind(self) -> None:
        sent, send = _collector()
        response = AsgiSocketResponse(send)

        await response.send(raw=b"a")
        await response.send(text="b")
        await response.send(json={"c": 1})
        await response.send(json={"d": 1}, encoder=lambda o: json.dumps(o, separators=(",", ":")))

        assert sent == [
            {"type": "websocket.send", "bytes": b"a"},
            {"type": "websocket.send", "text": "b"},
            {"type": "websocket.send", "text": '{"c": 1}'},
            {"type": "websocket.send", "text": '{"d":1}'},
        ]


class TestLifespan:
    async def test_startup_and_shutdown(self, make_app: AppFactory, cache: Cache) -> None:
        events: list[str] = []
        on_event(WEB_SERVER_STARTUP_COMPLETE_EVENT, cache=cache)(_recorder(events, "startup"))
        on_event(BLNT_STOPPED_EVENT, cache=cache)(_recorder(events, "stopped"))

        blnt = await make_app(start=False)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        sent = await client.lifespan("lifespan.startup", "lifespan.shutdown")

        assert [m["type"] for m in sent] == ["lifespan.startup.complete", "lifespan.shutdown.complete"]
        assert events == ["startup", "stopped"]

    async def test_startup_failure(self, cache: Cache, env_folder: Any) -> None:
        seen: list[Exception] = []

        @startup(cache=cache)
        async def failing() -> None:
            raise ValueError("boom")

        @on_event(WEB_SERVER_STARTUP_FAILED_EVENT, cache=cache)
        async def on_failed(context: EventContext[Exception]) -> None:
            seen.append(context.value)

        blnt = await make_bolinette([WebExtension()], cache=cache)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        sent = await client.lifespan("lifespan.startup", "lifespan.shutdown")

        assert [m["type"] for m in sent] == ["lifespan.startup.failed"]
        assert isinstance(seen[0], ValueError)

    async def test_shutdown_failure(self, cache: Cache, env_folder: Any) -> None:
        @on_event(BLNT_STOPPED_EVENT, cache=cache)
        async def on_stopped() -> None:
            raise ValueError("boom")

        blnt = await make_bolinette([WebExtension()], cache=cache)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        sent = await client.lifespan("lifespan.startup", "lifespan.shutdown")

        assert [m["type"] for m in sent] == ["lifespan.startup.complete", "lifespan.shutdown.failed"]


def _recorder(sink: list[str], label: str) -> Any:
    async def listener() -> None:
        sink.append(label)

    listener.__name__ = f"listener_{label}"
    return listener


class TestHttpScope:
    async def test_the_initialized_event_fires_once(self, make_app: AppFactory, cache: Cache) -> None:
        events: list[str] = []
        on_event(WEB_HTTP_INITIALIZED_EVENT, cache=cache)(_recorder(events, "http"))

        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        await client.request("GET", "/a")
        await client.request("GET", "/b")

        assert events == ["http"]

    async def test_an_early_disconnect_sends_nothing(self, make_app: AppFactory) -> None:
        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        result = await client.request("GET", "/a", events=[{"type": "http.disconnect"}])

        assert result.messages == []

    async def test_an_error_after_the_response_started_is_logged(self, make_app: AppFactory, cache: Cache) -> None:
        from collections.abc import AsyncIterator

        async def gen() -> AsyncIterator[str]:
            yield "partial"
            raise ValueError("boom")

        @controller("w", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> AsyncIterator[str]:
                return gen()

        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        result = await client.request("GET", "/w")

        assert result.status == 200
        assert result.text == "partial"

    async def test_dispatch_errors(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("i", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                return "ok"

        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        not_found = await client.request("GET", "/nope")
        not_allowed = await client.request("POST", "/i")

        assert (not_found.status, not_found.text) == (404, "404 Not Found")
        assert (not_allowed.status, not_allowed.text) == (405, "405 Method Not Allowed")


class TestWebSocketScope:
    async def test_the_initialized_event_fires_once(self, make_app: AppFactory, cache: Cache) -> None:
        events: list[str] = []
        on_event(WEB_WS_INITIALIZED_EVENT, cache=cache)(_recorder(events, "ws"))

        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())
        await client.websocket({"type": "websocket.connect"})
        await client.websocket({"type": "websocket.connect"})

        assert events == ["ws"]

    async def test_connect_is_accepted(self, make_app: AppFactory) -> None:
        blnt = await make_app()
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        sent = await client.websocket({"type": "websocket.connect"})

        assert sent == [{"type": "websocket.accept"}]


class TestCreateAsgiApp:
    async def test_async_factory(self, cache: Cache, env_folder: Any) -> None:
        apps: list[Bolinette] = []

        async def factory() -> Bolinette:
            blnt = await make_bolinette([WebExtension()], cache=cache)
            apps.append(blnt)
            return blnt

        client = AsgiClient(create_asgi_app(factory))
        sent = await client.lifespan("lifespan.startup", "lifespan.shutdown")

        assert [m["type"] for m in sent] == ["lifespan.startup.complete", "lifespan.shutdown.complete"]
        assert (await client.request("GET", "/nope")).status == 404

    async def test_sync_factory(self, cache: Cache, env_folder: Any) -> None:
        blnt = await make_bolinette([WebExtension()], cache=cache)
        client = AsgiClient(create_asgi_app(lambda: blnt))

        await client.lifespan("lifespan.startup")

        assert (await client.request("GET", "/nope")).status == 404
        await blnt.dispose()

    async def test_http_before_startup_is_unavailable(self, cache: Cache, env_folder: Any) -> None:
        client = AsgiClient(create_asgi_app(lambda: _never()))
        result = await client.request("GET", "/x")

        assert result.status == 503
        assert result.text == "503 Service Unavailable"

    async def test_websocket_before_startup_is_closed(self, cache: Cache, env_folder: Any) -> None:
        client = AsgiClient(create_asgi_app(lambda: _never()))

        assert await client.websocket() == [{"type": "websocket.close"}]

    async def test_shutdown_before_startup(self, cache: Cache, env_folder: Any) -> None:
        client = AsgiClient(create_asgi_app(lambda: _never()))

        assert await client.lifespan("lifespan.shutdown") == [{"type": "lifespan.shutdown.complete"}]

    async def test_a_failing_factory_reports_a_failed_startup(self, cache: Cache, env_folder: Any) -> None:
        def factory() -> Bolinette:
            raise ValueError("boom")

        client = AsgiClient(create_asgi_app(factory))

        assert await client.lifespan("lifespan.startup") == [{"type": "lifespan.startup.failed"}]


def _never() -> Bolinette:  # pragma: no cover
    raise AssertionError("the factory must not run")


class TestWebSocketAcceptFailure:
    async def test_a_failing_accept_is_logged_and_re_raised(self, make_app: AppFactory) -> None:
        blnt = await make_app()
        app = (await blnt.injector.require(AsgiApplication)).get_app()
        scope: dict[str, Any] = {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": "/ws",
            "query_string": b"",
            "headers": [],
        }

        async def receive() -> Any:
            return {"type": "websocket.connect"}

        async def send(message: Any) -> None:
            raise ConnectionError("socket gone")

        with pytest.raises(ConnectionError):
            await app(cast(Scope, scope), receive, send)
