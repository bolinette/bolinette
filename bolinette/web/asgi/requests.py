import json
from collections.abc import Awaitable, Callable
from typing import Any

from bolinette.web.asgi import HttpReceivedEvent, HttpRequestEvent


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
    ) -> None:
        self.method = method
        self.path = path
        self.headers = headers
        self.query_params = query_params
        self.path_params: dict[str, str] = {}


class AsgiWebRequest(AsgiRequest):
    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        received: HttpRequestEvent,
        receive: Callable[[], Awaitable[HttpReceivedEvent]],
    ) -> None:
        super().__init__(method, path, headers, query_params)
        self.body = AsgiAsyncBody(received, receive)

    async def bytes(self) -> bytes:
        return await self.body.read()

    async def text(self, encoding: str = "utf-8") -> str:
        return (await self.body.read()).decode(encoding)

    async def json(self) -> Any:
        return json.loads(await self.body.read())
