import json
from collections.abc import Callable
from typing import Any, Protocol, overload


class Response:
    def __init__(
        self,
        body: str | bytes | None = None,
        status: int = 200,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.body = body
        self.status = status
        self.headers = headers or {}
        self.headers["Content-Type"] = content_type


class WebSocketResponse(Protocol):
    @overload
    async def send(self, *, raw: bytes) -> None: ...

    @overload
    async def send(self, *, text: str) -> None: ...

    @overload
    async def send(self, *, json: Any, encoder: Callable[[object], str] = json.dumps) -> None: ...
