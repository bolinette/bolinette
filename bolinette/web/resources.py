import json
import traceback
from http import HTTPStatus
from typing import Any, NotRequired, TypedDict

from bolinette.core import Cache, Logger, meta
from bolinette.core.environment import CoreSection
from bolinette.core.injection import Injection, ScopedInjection, init_method
from bolinette.core.injection.resolver import ArgResolverOptions
from bolinette.core.mapping import JsonObjectEncoder, Mapper
from bolinette.core.mapping.exceptions import (
    ConvertionError,
    DestinationNotNullableError,
    MappingError,
    SourceNotFoundError,
    ValidationError,
)
from bolinette.core.types import Function, Type
from bolinette.core.utils import AttributeUtils
from bolinette.web import Payload, Response
from bolinette.web.abstract import Request
from bolinette.web.controller import Controller, ControllerMeta
from bolinette.web.exceptions import (
    BadRequestError,
    GroupedWebError,
    MethodNotAllowedDispatchError,
    MissingParameterError,
    NotFoundDispatchError,
    ParameterNotNullableError,
    WebError,
    WrongParameterTypeError,
)
from bolinette.web.middleware import Middleware, MiddlewareBag
from bolinette.web.routing import Route, RouteBucket, Router


class WebResources:
    def __init__(self, inject: Injection, logger: "Logger[WebResources]", core_section: CoreSection) -> None:
        self.inject = inject
        self.logger = logger
        self.core_section = core_section
        self.router = Router()

    @init_method
    def _init_ctrls(self, cache: Cache) -> None:
        for ctrl_cls in cache.get(ControllerMeta, hint=type[Controller], raises=False):
            ctrl_meta = meta.get(ctrl_cls, ControllerMeta)
            attr: Any
            for attr in AttributeUtils.get_cls_attrs(ctrl_cls).values():
                if not meta.has(attr, RouteBucket):
                    continue
                bucket = meta.get(attr, RouteBucket)
                for props in bucket.routes:
                    path = props.path
                    if not path.is_absolute:
                        path = ctrl_meta.path / path
                    if not path.is_absolute:
                        path.origin = f"/{path.origin}"
                    self.router.add_route(Route(props.method, path, Type(ctrl_cls), Function(attr)))

    async def dispatch(self, request: Request) -> Response:
        try:
            route = self.router.dispatch(request)
        except NotFoundDispatchError:
            return Response(status=404)
        except MethodNotAllowedDispatchError:
            return Response(status=405)
        handler = self.inject.instantiate(RouteHandler, named_args={"route": route})
        return await handler.handle(request)


class RouteHandler:
    def __init__(
        self,
        route: Route[..., Any],
        inject: Injection,
        core_section: CoreSection,
        logger: "Logger[RouteHandler]",
    ) -> None:
        self.route = route
        self.inject = inject
        self.core_section = core_section
        self.logger = logger

    @staticmethod
    def prepare_session(inject: Injection, request: Request) -> None:
        inject.add(Request, "scoped", instance=request)

    async def handle(self, request: Request) -> Response:
        self.logger.info(f"Received request on {request.path}")
        try:
            async with self.inject.get_async_scoped_session() as scoped_inject:
                self.prepare_session(scoped_inject, request)
                mdlws = self.collect_middlewares(scoped_inject)
                return await self.middleware_chain(request, scoped_inject, mdlws, 0)
        except Exception as err:
            self.logger.error(str(type(err)), str(err))
            if isinstance(err, WebError):
                status = err.status.value
                reason = err.status.phrase
                if isinstance(err, GroupedWebError):
                    errors = err.errors
                else:
                    errors = [err]
            else:
                status = HTTPStatus.INTERNAL_SERVER_ERROR.value
                reason = HTTPStatus.INTERNAL_SERVER_ERROR.phrase
                errors = [err]
            content: ErrorResponseContent = {
                "status": status,
                "reason": reason,
                "errors": [self._format_error(e) for e in errors],
            }
            if self.core_section.debug:
                content["debug"] = {
                    "type": str(type(err)),
                    "message": str(err),
                    "stacktrace": traceback.format_exc().split("\n"),
                }
            return Response(
                body=json.dumps(content),
                content_type="application/json",
                status=status,
            )

    async def middleware_chain(
        self,
        request: Request,
        scoped: ScopedInjection,
        mdlws: list[Middleware[Any]],
        index: int,
    ) -> Response:
        async def _next_handle() -> Response:
            return await self.middleware_chain(request, scoped, mdlws, index + 1)

        if index >= len(mdlws):
            return await self.call_controller(request, scoped)
        else:
            mdlw = mdlws[index]
            self.logger.debug(f"Calling middleware {mdlw}")
            return await scoped.call(mdlw.handle, args=[_next_handle])

    async def call_controller(
        self,
        request: Request,
        scoped: Injection,
    ) -> Response:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = None
        ctrl = scoped.instantiate(self.route.controller.cls)
        self.logger.debug(f"Calling controller route {self.route.func}(...)")
        result = await scoped.call(
            self.route.func.func,
            args=[ctrl],
            additional_resolvers=[
                RouteParamArgResolver(self.route, request),
                RoutePayloadArgResolver(self.route, scoped.require(Mapper), body),
            ],
        )
        if isinstance(result, Response):
            return result
        status: int
        match result:
            case [_, int()]:
                status = result[1]
                result = result[0]
            case _:
                status = 200
        match result:
            case str():
                content = result
                content_type = "text/plain"
            case int() | float() | bool():
                content = str(result)
                content_type = "text/plain"
            case _:
                content = json.dumps(result, cls=JsonObjectEncoder)
                content_type = "application/json"
        return Response(body=content, status=status, content_type=content_type)

    def collect_middlewares(self, scoped: Injection) -> list[Middleware[Any]]:
        bags: list[MiddlewareBag] = []
        if meta.has(self.route.controller.cls, MiddlewareBag):
            bags.append(meta.get(self.route.controller.cls, MiddlewareBag))
        if meta.has(self.route.func, MiddlewareBag):
            bags.append(meta.get(self.route.func, MiddlewareBag))
        mdlws: dict[Type[Middleware[...]], Middleware[...]] = {}
        for bag in bags:
            for t, mdlw_meta in reversed(bag.added.items()):
                mdlw = scoped.instantiate(t.cls)
                mdlw.options(*mdlw_meta.args, **mdlw_meta.kwargs)
                mdlws[t] = mdlw
            for t in bag.removed:
                if t in mdlws:
                    del mdlws[t]
        return list(mdlws.values())

    @staticmethod
    def _format_error(err: Exception) -> "ErrorDescription":
        if isinstance(err, WebError):
            message = err.message
            code = err.error_code
            params = err.error_args
        else:
            message = "Un unexpected error has occured while processing the request"
            code = "internal.error"
            params = {}
        f_err: ErrorDescription = {"message": message, "code": code, "params": params}
        return f_err


class RouteParamArgResolver:
    def __init__(self, route: Route[..., Any], request: Request) -> None:
        self.route = route
        self.request = request

    def supports(self, options: ArgResolverOptions) -> bool:
        return options.name in self.route.path.params

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
    def __init__(self, route: Route[..., Any], mapper: Mapper, body: Any | None) -> None:
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


class DebugErrorDetails(TypedDict):
    type: str
    message: str
    stacktrace: list[str]


class ErrorDescription(TypedDict):
    message: str
    code: str
    params: dict[str, Any]


class ErrorResponseContent(TypedDict):
    status: int
    reason: str
    errors: list[ErrorDescription]
    debug: NotRequired[DebugErrorDetails]
    errors: list[ErrorDescription]
    debug: NotRequired[DebugErrorDetails]
