import json
from collections.abc import Awaitable, Callable
from typing import Any, overload

from bolinette.web.asgi.types import WebSocketSendResult


class AsgiSocketResponse:
    def __init__(self, send: Callable[[WebSocketSendResult], Awaitable[None]]) -> None:
        self._send = send

    @overload
    async def send(self, *, raw: bytes) -> None: ...
    @overload
    async def send(self, *, text: str) -> None: ...
    @overload
    async def send(self, *, json: Any, encoder: Callable[[object], str] = json.dumps) -> None: ...

    async def send(self, **kwargs: Any):
        if "raw" in kwargs:
            self._send({"type": "websocket.send", "bytes": kwargs["raw"]})
        if "text" in kwargs:
            self._send({"type": "websocket.send", "text": kwargs["text"]})
        if "json" in kwargs:
            encoder: Callable[[object], str] = kwargs.get("encoder", json.dumps)
            await self._send({"type": "websocket.send", "text": encoder(kwargs["json"])})
