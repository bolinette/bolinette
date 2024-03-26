from typing import Any, Protocol


class Request(Protocol):
    method: str
    path: str
    headers: dict[str, str]
    query_params: dict[str, str]
    path_params: dict[str, str]

    async def bytes(self) -> bytes: ...

    async def text(self, encoding: str = "utf-8") -> str: ...

    async def json(self) -> Any: ...
