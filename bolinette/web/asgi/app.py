from collections.abc import Awaitable, Callable
from typing import Any

from bolinette.core.bolinette import Bolinette
from bolinette.web.asgi import (
    AsgiCallable,
    AsgiRequest,
    AsgiResponse,
    AsgiSocketRequest,
    AsgiSocketResponse,
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
from bolinette.web.resources import WebResources
from bolinette.web.ws import WebSocketHandler


class AsgiApplication:
    def __init__(self, blnt: Bolinette) -> None:
        self._blnt = blnt
        self._resources: WebResources | None = None
        self._ws_handler: WebSocketHandler | None = None

    async def _handle_startup(
        self,
        send: Callable[[LifespanStartupResult], Awaitable[None]],
    ) -> None:
        try:
            await self._blnt.startup()
            self._blnt.injection.add(AsgiApplication, "singleton", instance=self)
            await send({"type": "lifespan.startup.complete"})
        except BaseException:
            await send({"type": "lifespan.startup.failed"})

    async def _handle_shutdown(
        self,
        send: Callable[[LifespanShutdownResult], Awaitable[None]],
    ) -> None:
        try:
            await send({"type": "lifespan.shutdown.complete"})
        except BaseException:
            await send({"type": "lifespan.shutdown.failed"})

    async def _handle_lifespan(
        self,
        receive: Callable[[], Awaitable[LifespanReceivedEvent]],
        send: Callable[[LifespanResult], Awaitable[None]],
    ) -> None:
        received = await receive()
        match received["type"]:
            case "lifespan.startup":
                await self._handle_startup(send)
            case "lifespan.shutdown":
                await self._handle_shutdown(send)

    async def _handle_http_request(
        self,
        scope: HttpScope,
        received: HttpRequestEvent,
        receive: Callable[[], Awaitable[HttpReceivedEvent]],
        send: Callable[[HttpResponseResult], Awaitable[None]],
    ) -> None:
        if self._resources is None:
            self._resources = self._blnt.injection.require(WebResources)

        request = AsgiRequest(scope["method"], scope["path"], {}, {}, received, receive)
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
                raise NotImplementedError()

    async def _handle_ws_connect(
        self,
        send: Callable[[WebSocketConnectResult], Awaitable[None]],
    ) -> None:
        try:
            await send({"type": "websocket.accept"})
        except BaseException:
            await send({"type": "websocket.close"})

    async def _handle_ws(
        self,
        scope: WebSocketScope,
        receive: Callable[[], Awaitable[WebSocketReceivedEvent]],
        send: Callable[[WebSocketResult], Awaitable[None]],
    ) -> None:
        response = AsgiSocketResponse(send)
        if self._ws_handler is None:
            self._ws_handler = self._blnt.injection.require(WebSocketHandler)
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
