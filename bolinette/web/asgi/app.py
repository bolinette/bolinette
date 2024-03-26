import json
from collections.abc import Awaitable, Callable
from typing import Any

from bolinette.core.bolinette import Bolinette
from bolinette.web import WebResources
from bolinette.web.asgi import (
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
)


class AsgiApplication:
    def __init__(self, blnt: Bolinette) -> None:
        self._blnt = blnt

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
        resources = self._blnt.injection.require(WebResources)
        request = AsgiRequest(scope["method"], scope["path"], {}, {}, AsgiAsyncBody(received, receive))

        response = await resources.dispatch(request)

        match response.body:
            case bytes():
                body = response.body
            case str():
                body: bytes = response.body.encode()
            case None:
                body = b""

        await send(
            {
                "type": "http.response.start",
                "status": response.status,
                "headers": [(k.encode(), v.encode()) for k, v in response.headers.items()],
            }
        )
        await send({"type": "http.response.body", "body": body, "more_body": False})

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
                ...

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

        return app


class AsgiAsyncBody:
    def __init__(
        self,
        received: HttpRequestEvent,
        receive: Callable[[], Awaitable[HttpReceivedEvent]],
    ) -> None:
        self.chunks = [received.get("body", b"")]
        self.more = received.get("more_body", False)
        self.receive = receive

    async def read(self) -> bytes:
        while self.more:
            received = await self.receive()
            self.chunks.append(received.get("body", b""))
            self.more = received.get("more_body", False)
        return b"".join(self.chunks)


class AsgiRequest:
    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        body: AsgiAsyncBody,
    ) -> None:
        self.method = method
        self.path = path
        self.headers = headers
        self.query_params = query_params
        self.path_params: dict[str, str] = {}
        self.body = body

    async def bytes(self) -> bytes:
        return await self.body.read()

    async def text(self, encoding: str = "utf-8") -> str:
        return (await self.body.read()).decode(encoding)

    async def json(self) -> Any:
        return json.loads(await self.body.read())
