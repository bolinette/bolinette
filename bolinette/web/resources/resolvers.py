from http import HTTPStatus
from typing import Any

from bolinette.core.injection.resolver import ArgResolverOptions
from bolinette.core.mapping import Mapper
from bolinette.core.mapping.exceptions import (
    ConvertionError,
    DestinationNotNullableError,
    MappingError,
    SourceNotFoundError,
    ValidationError,
)
from bolinette.web import Payload
from bolinette.web.abstract import Request
from bolinette.web.exceptions import (
    BadRequestError,
    GroupedWebError,
    MissingParameterError,
    ParameterNotNullableError,
    WebError,
    WrongParameterTypeError,
)
from bolinette.web.routing import Route


class RouteParamArgResolver:
    def __init__(self, route: Route[..., Any], request: Request) -> None:
        self.route = route
        self.request = request

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.name in self.request.path_params

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        value = self.request.path_params[options.name]
        t = options.t
        match t.cls:
            case cls if cls is int:
                value = int(value)
            case cls if cls is float:
                value = float(value)
            case cls if cls is bool:
                value = bool(value)
            case cls if cls is not str:
                raise Exception()  # TODO: Lever une vraie exception
            case _:
                pass
        return (options.name, value)


class RoutePayloadArgResolver:
    def __init__(self, route: Route[..., Any], mapper: Mapper, body: object | None) -> None:
        self.route = route
        self.mapper = mapper
        self.body = body

    def supports(self, options: ArgResolverOptions) -> bool:
        return any(
            isinstance(a, Payload) or (isinstance(a, type) and issubclass(a, Payload)) for a in options.t.annotated
        )

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        if self.body is None:
            if options.t.nullable:
                return options.name, None
            raise BadRequestError(
                "Payload expected but none provided",
                "payload.expected",
                ctrl=self.route.controller,
                route=self.route.func,
            )
        try:
            payload = self.mapper.map(type(self.body), options.t.cls, self.body, validate=True)
        except ValidationError as err:
            raise GroupedWebError(
                [self._transform_error(e) for e in err.errors],
                HTTPStatus.BAD_REQUEST,
                ctrl=self.route.controller,
                route=self.route.func,
            ) from err
        return options.name, payload

    def _transform_error(self, err: MappingError) -> WebError:
        match err:
            case SourceNotFoundError():
                return MissingParameterError(
                    err.dest,
                    ctrl=self.route.controller,
                    route=self.route.func,
                )
            case DestinationNotNullableError():
                return ParameterNotNullableError(
                    err.dest,
                    ctrl=self.route.controller,
                    route=self.route.func,
                )
            case ConvertionError():
                return WrongParameterTypeError(
                    err.dest,
                    err.target,
                    ctrl=self.route.controller,
                    route=self.route.func,
                )
            case _:
                raise NotImplementedError(type(err), err) from err
