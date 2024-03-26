import json
from collections.abc import Awaitable, Callable
from typing import Any, overload

from bolinette.web.abstract import ResponseState
from bolinette.web.asgi.types import HttpResponseResult, WebSocketSendResult
from bolinette.web.exceptions import InternalServerError


class AsgiResponse:
    def __init__(self, send: Callable[[HttpResponseResult], Awaitable[None]]) -> None:
        self._send = send
        self._status: int = 200
        self._headers: dict[str, str] = {}
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
        if self._state != ResponseState.Idle:
            raise InternalServerError("Response already started")
        await self._send(
            {
                "type": "http.response.start",
                "status": self._status,
                "headers": [(k.encode(), v.encode()) for k, v in self._headers.items()],
            }
        )
        self._state = ResponseState.Started

    async def close(self) -> None:
        match self._state:
            case ResponseState.Idle:
                raise InternalServerError("Response has not started")
            case ResponseState.Closed:
                raise InternalServerError("Response has been closed")
            case ResponseState.Sending | ResponseState.Started:
                await self._send({"type": "http.response.body", "body": b"", "more_body": False})
                self._state = ResponseState.Closed

    async def write(self, raw: bytes) -> None:
        match self._state:
            case ResponseState.Sending:
                await self._send({"type": "http.response.body", "body": raw, "more_body": True})
            case ResponseState.Started:
                await self._send({"type": "http.response.body", "body": raw, "more_body": True})
                self._state = ResponseState.Sending
            case ResponseState.Idle:
                raise InternalServerError("Response has not started")
            case ResponseState.Closed:
                raise InternalServerError("Response has been closed")

    def set_status(self, status: int, /) -> None:
        self._status = status

    def set_header(self, key: str, value: str, /) -> None:
        self._headers[key] = value

    def has_header(self, key: str, /) -> bool:
        return key in self._headers

    def unset_header(self, key: str, /) -> None:
        if key in self._headers:
            del self._headers[key]


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
