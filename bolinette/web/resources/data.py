from http import HTTPStatus
from typing import Any, overload

from bolinette.web.resources import HttpHeaders


class ResponseData:
    def __init__(self, *, status: HTTPStatus = HTTPStatus.OK, headers: dict[str, str] | None = None) -> None:
        self._status = status
        self._headers = headers or {}

    @property
    def status(self) -> HTTPStatus:
        return self._status

    def set_status(self, value: HTTPStatus | int, /) -> None:
        if isinstance(value, HTTPStatus):
            self._status = value
        else:
            self._status = HTTPStatus(value)

    @property
    def headers(self) -> dict[str, str]:
        return {**self._headers}

    @overload
    def get_header(self, key: str, /) -> str: ...
    @overload
    def get_header[T](self, key: str, default: T, /) -> str | T: ...

    def get_header(self, key: str, /, *args: Any) -> Any:
        if len(args):
            return self._headers.get(key, args[0])
        return self._headers[key]

    def set_header(self, key: str, value: str, /) -> None:
        self._headers[key] = value

    def set_headers(self, values: dict[str, str], /) -> None:
        self._headers = self._headers | values

    def has_header(self, key: str, /) -> bool:
        return key in self._headers

    def set_content_type(self, value: str, /) -> None:
        self.set_header(HttpHeaders.ContentType, value)
