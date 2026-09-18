from collections.abc import Callable
from http import HTTPStatus
from typing import Any

import pytest
from peritype import FWrap, TWrap, wrap_func, wrap_type

from bolinette.core.expressions import ExpressionTree
from bolinette.web.exceptions import (
    BadRequestError,
    DispatchError,
    ForbiddenError,
    GroupedWebError,
    InternalServerError,
    MethodNotAllowedDispatchError,
    MissingParameterError,
    NotFoundDispatchError,
    NotFoundError,
    ParameterNotNullableError,
    UnauthorizedError,
    WebError,
    WebErrorHandler,
    WrongParameterTypeError,
)


class Ctrl:
    def route(self) -> None:
        pass


def _ctrl() -> TWrap[Any]:
    return wrap_type(Ctrl)


def _route() -> FWrap[..., Any]:
    return wrap_func(Ctrl.route)


def _expr() -> Any:
    return ExpressionTree.new(dict[str, Any]).name


class TestWebError:
    def test_str_without_args(self) -> None:
        err = WebError("boom", "some.code", HTTPStatus.IM_A_TEAPOT)

        assert str(err) == "some.code"
        assert err.message == "boom"
        assert err.status is HTTPStatus.IM_A_TEAPOT
        assert err.error_args == {}

    def test_str_with_args(self) -> None:
        err = WebError("boom", "some.code", HTTPStatus.IM_A_TEAPOT, {"a": 1, "b": "x"})

        assert str(err) == "some.code|a:1|b:x"

    def test_message_carries_controller_and_route(self) -> None:
        err = WebError("boom", "some.code", HTTPStatus.IM_A_TEAPOT, ctrl=_ctrl(), route=_route())

        assert err.message == "Controller Ctrl, Route Ctrl.route, boom"


class TestErrorSubclasses:
    @pytest.mark.parametrize(
        ("cls", "status"),
        [
            (BadRequestError, HTTPStatus.BAD_REQUEST),
            (ForbiddenError, HTTPStatus.FORBIDDEN),
            (UnauthorizedError, HTTPStatus.UNAUTHORIZED),
            (NotFoundError, HTTPStatus.NOT_FOUND),
        ],
    )
    def test_status_shortcuts(self, cls: Callable[..., WebError], status: HTTPStatus) -> None:
        err = cls("boom", "some.code", {"a": 1}, ctrl=_ctrl(), route=_route())

        assert err.status is status
        assert err.error_args == {"a": 1}

    def test_internal_server_error_defaults_its_code(self) -> None:
        err = InternalServerError("boom")

        assert err.status is HTTPStatus.INTERNAL_SERVER_ERROR
        assert err.error_code == "internal.web.exception"

    def test_internal_server_error_keeps_a_given_code(self) -> None:
        assert InternalServerError("boom", "custom.code").error_code == "custom.code"


class TestPayloadErrors:
    def test_missing_parameter(self) -> None:
        err = MissingParameterError(_expr(), ctrl=_ctrl(), route=_route())

        assert err.error_code == "payload.parameter.missing"
        assert err.error_args == {"path": "name"}
        assert "Parameter 'name' is missing in payload" in err.message

    def test_not_nullable_parameter(self) -> None:
        err = ParameterNotNullableError(_expr())

        assert err.error_code == "payload.parameter.not_nullable"
        assert "must not be null" in err.message

    def test_wrong_parameter_type(self) -> None:
        err = WrongParameterTypeError(_expr(), wrap_type(int))

        assert err.error_code == "payload.parameter.wrong_type"
        assert "could not be converted to 'int'" in err.message


class TestGroupedWebError:
    def test_collects_errors(self) -> None:
        first = BadRequestError("one", "a")
        group = GroupedWebError([first], HTTPStatus.BAD_REQUEST, ctrl=_ctrl(), route=_route())
        second = BadRequestError("two", "b")

        group.add(second)

        assert group.errors == [first, second]
        assert group.error_code == "internal.web.exception"


class TestDispatchErrors:
    def test_not_found(self) -> None:
        err = NotFoundDispatchError("/items")

        assert isinstance(err, DispatchError)
        assert err.message == "Route /items, Route not found"

    def test_method_not_allowed(self) -> None:
        assert MethodNotAllowedDispatchError("/items").message == "Route /items, Method not allowed"


class TestWebErrorHandler:
    def test_web_error_payload(self) -> None:
        status, content = WebErrorHandler.create_error_payload(BadRequestError("boom", "a.b", {"x": 1}), False)

        assert status is HTTPStatus.BAD_REQUEST
        assert content == {
            "status": 400,
            "reason": "Bad Request",
            "errors": [{"message": "boom", "code": "a.b", "params": {"x": 1}}],
        }

    def test_grouped_error_payload_lists_every_error(self) -> None:
        group = GroupedWebError(
            [BadRequestError("one", "a"), BadRequestError("two", "b")],
            HTTPStatus.BAD_REQUEST,
        )

        _, content = WebErrorHandler.create_error_payload(group, False)

        assert [e["code"] for e in content["errors"]] == ["a", "b"]

    def test_unknown_error_payload(self) -> None:
        status, content = WebErrorHandler.create_error_payload(ValueError("boom"), False)

        assert status is HTTPStatus.INTERNAL_SERVER_ERROR
        assert content["errors"] == [
            {
                "message": "An unexpected error has occurred while processing the request",
                "code": "internal.error",
                "params": {},
            }
        ]
        assert "debug" not in content

    def test_debug_adds_the_stacktrace(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError as err:
            _, content = WebErrorHandler.create_error_payload(err, True)

        debug = content.get("debug")
        assert debug is not None
        assert debug["message"] == "boom"
        assert debug["type"] == str(ValueError)
        assert any("ValueError" in line for line in debug["stacktrace"])
