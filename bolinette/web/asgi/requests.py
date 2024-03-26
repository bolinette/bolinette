import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal

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
        received: HttpRequestEvent,
        receive: Callable[[], Awaitable[HttpReceivedEvent]],
    ) -> None:
        self.method = method
        self.path = path
        self.headers = headers
        self.query_params = query_params
        self.path_params: dict[str, str] = {}
        self._body = AsgiAsyncBody(received, receive)

    async def raw(self) -> bytes:
        return await self._body.read()

    async def text(self, *, encoding: str = "utf-8") -> str:
        return (await self._body.read()).decode(encoding)

    async def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any:
        return json.loads(await self._body.read(), cls=cls)


class AsgiSocketRequest:
    def __init__(
        self,
        bytes: bytes | None,
        text: str | None,
    ) -> None:
        self._bytes = bytes
        self._text = text

    def get_type(self) -> Literal["raw", "text"]:
        if self._bytes is not None:
            return "raw"
        return "text"

    def raw(self) -> bytes:
        if self._bytes is None:
            raise TypeError("This request has a unicode content")
        return self._bytes

    def text(self) -> str:
        if self._text is None:
            raise TypeError("This request has a raw content")
        return self._text

    def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any:
        if self._bytes is not None:
            return json.loads(self._bytes, cls=cls)
        if self._text is not None:
            return json.loads(self._text, cls=cls)
