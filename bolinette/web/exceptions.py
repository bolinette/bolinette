from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from typing_extensions import override

from bolinette.core.exceptions import BolinetteError, ParameterError
from bolinette.core.types import Type
from bolinette.web.controller import Controller


class WebError(BolinetteError, ParameterError):
    def __init__(
        self,
        message: str,
        error_code: str,
        status: HTTPStatus,
        error_args: dict[str, Any] | None = None,
        *,
        ctrl: Type[Controller] | None = None,
        route: Callable[..., Any] | None = None,
    ) -> None:
        ParameterError.__init__(self, ctrl="Controller {}", route="Route {}")
        BolinetteError.__init__(self, self._format_params(message, ctrl=ctrl, route=route))
        self.error_code = error_code
        self.status = status
        self.error_args = error_args or {}

    @override
    def __str__(self) -> str:
        if not self.error_args:
            return self.error_code
        return f"{self.error_code}|{'|'.join(f'{k}:{v}' for k,v in self.error_args.items())}"


class BadRequestError(WebError):
    def __init__(
        self,
        message: str,
        error_code: str,
        error_args: dict[str, Any] | None = None,
        *,
        ctrl: Type[Controller] | None = None,
        route: Callable[..., Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, HTTPStatus.BAD_REQUEST, error_args, ctrl=ctrl, route=route)
