import json
from http import HTTPStatus
from typing import Any, override

from peritype import TWrap
from soupape.extension import AnnotatedResolutionFunction, CallerContext, ResolutionContext

from bolinette.core.mapping import Mapper
from bolinette.core.mapping.exceptions import (
    ConversionError,
    DestinationNotNullableError,
    MappingError,
    SourceNotFoundError,
    ValidationError,
)
from bolinette.web._abstract import Request
from bolinette.web._routing import Route
from bolinette.web.exceptions import (
    BadRequestError,
    GroupedWebError,
    InternalServerError,
    MissingParameterError,
    ParameterNotNullableError,
    WebError,
    WrongParameterTypeError,
)


def _caller_context(context: ResolutionContext, marker: str) -> CallerContext:
    if context.caller_context is None:  # pragma: no cover
        raise TypeError(f"A {marker} can only resolve a function parameter")
    return context.caller_context


def _required(context: ResolutionContext, marker: str) -> TWrap[Any]:
    if context.required is None:  # pragma: no cover
        raise TypeError(f"A {marker} can only resolve an annotated parameter")
    return context.required


def _convert(value: str, required: TWrap[Any], param_name: str) -> Any:
    try:
        match required.inner_type:
            case cls if cls is int:
                return int(value)
            case cls if cls is float:
                return float(value)
            case cls if cls is bool:
                return value.lower() in ("1", "true")
            case cls if cls is str:
                return value
            case _:
                raise InternalServerError(f"Could not inject param '{param_name}' of type {required}")
    except ValueError as err:
        raise BadRequestError(
            f"Unable to convert {param_name} to type {required}",
            "web.route.param.wrong_type",
        ) from err


def _absent(context: ResolutionContext, caller: CallerContext, required: TWrap[Any], error: WebError) -> Any:
    del context
    if caller.has_default_value:
        return caller.default_value
    if required.nullable:
        return None
    raise error


class PathParam(AnnotatedResolutionFunction):
    @override
    def __resolve__(self, context: ResolutionContext, request: Request) -> Any:
        caller = _caller_context(context, "path parameter")
        required = _required(context, "path parameter")
        name = caller.param_name
        if name not in request.path_params:
            return _absent(
                context,
                caller,
                required,
                BadRequestError(f"Path parameter '{name}' is missing", "web.route.param.missing", {"name": name}),
            )
        return _convert(request.path_params[name], required, name)


class QueryParam(AnnotatedResolutionFunction):
    @override
    def __resolve__(self, context: ResolutionContext, request: Request) -> Any:
        caller = _caller_context(context, "query parameter")
        required = _required(context, "query parameter")
        name = caller.param_name
        if name not in request.query_params or not request.query_params[name]:
            return _absent(
                context,
                caller,
                required,
                BadRequestError(f"Query parameter '{name}' is missing", "web.route.query.missing", {"name": name}),
            )
        values = request.query_params[name]
        if required.inner_type is list:
            element = required.generic_params[0]
            return [_convert(value, element, name) for value in values]
        return _convert(values[-1], required, name)


class Payload(AnnotatedResolutionFunction):
    @override
    async def __resolve__(
        self,
        context: ResolutionContext,
        request: Request,
        mapper: Mapper,
        route: Route,
    ) -> Any:
        caller = _caller_context(context, "payload")
        required = _required(context, "payload")
        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = None
        if body is None:
            return _absent(
                context,
                caller,
                required,
                BadRequestError(
                    "Payload expected but none provided",
                    "payload.expected",
                    ctrl=route.controller,
                    route=route.func,
                ),
            )
        match body:
            case dict():
                src_cls: type[Any] = dict[str, Any]
            case list():
                src_cls = list[Any]
            case _:
                raise _invalid_payload(required, route)
        try:
            return mapper.map(src_cls, required.nodes[0].origin, body, validate=True)
        except ValidationError as err:
            raise build_payload_error(err, required, route) from err


def build_payload_error(err: ValidationError, required: TWrap[Any], route: Route) -> GroupedWebError:
    return GroupedWebError(
        [_transform_error(e, required, route) for e in err.errors],
        HTTPStatus.BAD_REQUEST,
        ctrl=route.controller,
        route=route.func,
    )


def _invalid_payload(required: TWrap[Any], route: Route) -> BadRequestError:
    return BadRequestError(
        f"Payload could not be mapped to {required}",
        "payload.invalid",
        {"type": str(required)},
        ctrl=route.controller,
        route=route.func,
    )


def _transform_error(err: MappingError, required: TWrap[Any], route: Route) -> WebError:
    if err.dest is None:
        return _invalid_payload(required, route)
    match err:
        case SourceNotFoundError():
            return MissingParameterError(err.dest, ctrl=route.controller, route=route.func)
        case DestinationNotNullableError():
            return ParameterNotNullableError(err.dest, ctrl=route.controller, route=route.func)
        case ConversionError() if err.target is not None:
            return WrongParameterTypeError(err.dest, err.target, ctrl=route.controller, route=route.func)
        case _:
            return _invalid_payload(required, route)
