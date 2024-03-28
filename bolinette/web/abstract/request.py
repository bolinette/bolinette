import json
from typing import Any, Literal, Protocol


class Request(Protocol):
    method: str
    path: str
    headers: dict[str, str]
    query_params: dict[str, str]
    path_params: dict[str, str]

    async def raw(self) -> bytes: ...

    async def text(self, *, encoding: str = "utf-8") -> str: ...

    async def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any: ...


class WebSocketRequest(Protocol):
    def get_type(self) -> Literal["raw", "text"]: ...

    def raw(self) -> bytes: ...

    def text(self) -> str: ...

    def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any: ...
