import json
from collections.abc import Callable
from enum import Enum, auto, unique
from typing import Any, Protocol, overload


@unique
class ResponseState(Enum):
    Idle = auto()  # Has not started yet
    Started = auto()  # Has sent headers, but no body yet
    Sending = auto()  # Has started streaming body
    Closed = auto()  # Has been closed


class Response(Protocol):
    @property
    def status(self) -> int: ...
    @property
    def headers(self) -> dict[str, str]: ...
    @property
    def state(self) -> ResponseState: ...

    async def open(self) -> None: ...

    async def close(self) -> None: ...

    async def write(self, raw: bytes) -> None: ...

    def set_status(self, status: int, /) -> None: ...

    def set_header(self, key: str, value: str, /) -> None: ...

    def has_header(self, key: str, /) -> bool: ...

    def unset_header(self, key: str, /) -> None: ...


class WebSocketResponse(Protocol):
    @overload
    async def send(self, *, raw: bytes) -> None: ...
    @overload
    async def send(self, *, text: str) -> None: ...
    @overload
    async def send(self, *, json: Any, encoder: Callable[[object], str] = json.dumps) -> None: ...
