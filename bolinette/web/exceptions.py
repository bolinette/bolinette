from http import HTTPStatus
from typing import Any, override

from bolinette.core.exceptions import BolinetteError, ParameterError
from bolinette.core.expressions import ExpressionNode, ExpressionTree
from bolinette.core.types import Function, Type
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
        route: Function[..., Any] | None = None,
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


class GroupedWebError(WebError):
    def __init__(
        self,
        errors: list[WebError],
        status: HTTPStatus,
        *,
        ctrl: Type[Controller] | None = None,
        route: Function[..., Any] | None = None,
    ) -> None:
        super().__init__(
            "Error raised during route executions",
            "internal.web.exception",
            status,
            {},
            ctrl=ctrl,
            route=route,
        )
        self.errors = errors

    def add(self, *errors: WebError) -> None:
        self.errors.extend(errors)


class BadRequestError(WebError):
    def __init__(
        self,
        message: str,
        error_code: str,
        error_args: dict[str, Any] | None = None,
        *,
        ctrl: Type[Controller] | None = None,
        route: Function[..., Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, HTTPStatus.BAD_REQUEST, error_args, ctrl=ctrl, route=route)


class MissingParameterError(BadRequestError):
    def __init__(
        self,
        expr: ExpressionNode,
        *,
        ctrl: Type[Controller] | None = None,
        route: Function[..., Any] | None = None,
    ) -> None:
        path = ExpressionTree.format(expr, max_depth=1)
        super().__init__(
            f"Parameter '{path}' is missing in payload",
            "payload.parameter.missing",
            {"path": path},
            ctrl=ctrl,
            route=route,
        )


class ParameterNotNullableError(BadRequestError):
    def __init__(
        self,
        expr: ExpressionNode,
        *,
        ctrl: Type[Controller] | None = None,
        route: Function[..., Any] | None = None,
    ) -> None:
        path = ExpressionTree.format(expr, max_depth=1)
        super().__init__(
            f"Parameter '{path}' must not be null",
            "payload.parameter.not_nullable",
            {"path": path},
            ctrl=ctrl,
            route=route,
        )


class WrongParameterTypeError(BadRequestError):
    def __init__(
        self,
        expr: ExpressionNode,
        target: Type[Any],
        *,
        ctrl: Type[Controller] | None = None,
        route: Function[..., Any] | None = None,
    ) -> None:
        path = ExpressionTree.format(expr, max_depth=1)
        super().__init__(
            f"Parameter '{path}' could be converted to '{target}'",
            "payload.parameter.wrong_type",
            {"path": path},
            ctrl=ctrl,
            route=route,
        )
