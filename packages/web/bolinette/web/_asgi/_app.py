import logging
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import parse_qs

from bolinette.core import Bolinette, Logger
from bolinette.core.__main__ import AppFactory, build_app
from bolinette.core.events import EventContext
from bolinette.web._asgi._requests import AsgiRequest, AsgiSocketRequest
from bolinette.web._asgi._responses import AsgiResponse, AsgiSocketResponse
from bolinette.web._asgi._types import (
    AsgiCallable,
    HttpReceivedEvent,
    HttpRequestEvent,
    HttpResponseResult,
    HttpScope,
    LifespanReceivedEvent,
    LifespanResult,
    LifespanShutdownResult,
    LifespanStartupResult,
    Scope,
    WebSocketConnectResult,
    WebSocketReceivedEvent,
    WebSocketResult,
    WebSocketScope,
)
from bolinette.web._events import (
    WEB_HTTP_INITIALIZED_EVENT,
    WEB_SERVER_STARTUP_COMPLETE_EVENT,
    WEB_SERVER_STARTUP_FAILED_EVENT,
    WEB_WS_INITIALIZED_EVENT,
)
from bolinette.web._resources import WebResources
from bolinette.web.ws._handler import WebSocketHandler


class AsgiApplication:
    def __init__(
        self,
        blnt: Bolinette,
        resources: WebResources,
        ws_handler: WebSocketHandler,
        logger: "Logger[AsgiApplication]",
    ) -> None:
        self._blnt = blnt
        self._resources = resources
        self._ws_handler = ws_handler
        self._logger = logger
        self._http_initialized = False
        self._ws_initialized = False

    async def _handle_startup(self, send: Callable[[LifespanStartupResult], Awaitable[None]]) -> bool:
        try:
            await self._blnt.startup()
            await send({"type": "lifespan.startup.complete"})
            await self._blnt.dispatch_event(WEB_SERVER_STARTUP_COMPLETE_EVENT)
        except BaseException as err:
            self._logger.error("Server startup failed", exc_info=err)
            await send({"type": "lifespan.startup.failed"})
            await self._blnt.dispatch_event(WEB_SERVER_STARTUP_FAILED_EVENT, context=EventContext(err))
            return False
        return True

    async def _handle_shutdown(self, send: Callable[[LifespanShutdownResult], Awaitable[None]]) -> None:
        try:
            await self._blnt.dispose()
            await send({"type": "lifespan.shutdown.complete"})
        except BaseException as err:
            self._logger.error("Server shutdown failed", exc_info=err)
            await send({"type": "lifespan.shutdown.failed"})

    async def _handle_lifespan(
        self,
        receive: Callable[[], Awaitable[LifespanReceivedEvent]],
        send: Callable[[LifespanResult], Awaitable[None]],
    ) -> None:
        while True:
            received = await receive()
            match received["type"]:
                case "lifespan.startup":
                    if not await self._handle_startup(send):
                        break
                case "lifespan.shutdown":
                    await self._handle_shutdown(send)
                    break

    async def _handle_http_request(
        self,
        scope: HttpScope,
        received: HttpRequestEvent,
        receive: Callable[[], Awaitable[HttpReceivedEvent]],
        send: Callable[[HttpResponseResult], Awaitable[None]],
    ) -> None:
        if not self._http_initialized:
            self._http_initialized = True
            await self._blnt.dispatch_event(WEB_HTTP_INITIALIZED_EVENT)
        headers = {k.decode().lower(): v.decode() for (k, v) in scope["headers"]}
        query = parse_qs(scope["query_string"].decode(), keep_blank_values=True)
        request = AsgiRequest(scope["method"], scope["path"], headers, query, received, receive)
        response = AsgiResponse(send)
        await self._resources.dispatch(request, response)

    async def _handle_http(
        self,
        scope: HttpScope,
        receive: Callable[[], Awaitable[HttpReceivedEvent]],
        send: Callable[[HttpResponseResult], Awaitable[None]],
    ) -> None:
        received = await receive()
        match received["type"]:
            case "http.request":
                await self._handle_http_request(scope, received, receive, send)
            case "http.disconnect":
                return

    async def _handle_ws_connect(self, send: Callable[[WebSocketConnectResult], Awaitable[None]]) -> None:
        try:
            await send({"type": "websocket.accept"})
        except BaseException as err:
            self._logger.error("Could not accept the websocket connection", exc_info=err)
            raise

    async def _handle_ws(
        self,
        scope: WebSocketScope,
        receive: Callable[[], Awaitable[WebSocketReceivedEvent]],
        send: Callable[[WebSocketResult], Awaitable[None]],
    ) -> None:
        del scope
        if not self._ws_initialized:
            self._ws_initialized = True
            await self._blnt.dispatch_event(WEB_WS_INITIALIZED_EVENT)
        response = AsgiSocketResponse(send)
        while True:
            received = await receive()
            match received["type"]:
                case "websocket.connect":
                    await self._handle_ws_connect(send)
                case "websocket.receive":
                    request = AsgiSocketRequest(received.get("bytes", None), received.get("text", None))
                    await self._ws_handler.handle(request, response)
                case "websocket.disconnect":
                    await self._ws_handler.remove_connection(response)
                    break

    def get_app(self) -> AsgiCallable:
        async def app(
            scope: Scope,
            receive: Callable[[], Awaitable[Any]],
            send: Callable[[Any], Awaitable[None]],
        ) -> None:
            match scope["type"]:
                case "lifespan":
                    await self._handle_lifespan(receive, send)
                case "http":
                    await self._handle_http(scope, receive, send)
                case "websocket":
                    await self._handle_ws(scope, receive, send)

        return app


def create_asgi_app(app_factory: AppFactory) -> AsgiCallable:
    logger = logging.getLogger(f"{__name__}.create_asgi_app")
    state: dict[str, AsgiCallable] = {}

    def _replay_once(first: Any, receive: Callable[[], Awaitable[Any]]) -> Callable[[], Awaitable[Any]]:
        pending = [first]

        async def _receive() -> Any:
            if pending:
                return pending.pop()
            return await receive()

        return _receive

    async def _start(receive: Callable[[], Awaitable[Any]], send: Callable[[Any], Awaitable[None]]) -> None:
        try:
            blnt = await build_app(app_factory)
            app = (await blnt.injector.require(AsgiApplication)).get_app()
        except Exception:
            logger.exception("Could not build the Bolinette application")
            await send({"type": "lifespan.startup.failed"})
            return
        state["app"] = app
        await app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)

    async def _not_started(scope: Scope, send: Callable[[Any], Awaitable[None]]) -> None:
        logger.error("Received a %s request before the application started", scope["type"])
        if scope["type"] == "websocket":
            await send({"type": "websocket.close"})
            return
        await send(
            {
                "type": "http.response.start",
                "status": 503,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send({"type": "http.response.body", "body": b"503 Service Unavailable", "more_body": False})

    async def app(
        scope: Scope,
        receive: Callable[[], Awaitable[Any]],
        send: Callable[[Any], Awaitable[None]],
    ) -> None:
        if "app" in state:
            await state["app"](scope, receive, send)
            return
        if scope["type"] == "lifespan":
            received = await receive()
            if received["type"] == "lifespan.startup":
                await _start(_replay_once(received, receive), send)
            else:
                await send({"type": "lifespan.shutdown.complete"})
            return
        await _not_started(scope, send)

    return app
