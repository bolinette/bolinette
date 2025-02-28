import json
from collections.abc import Callable
from http import HTTPStatus
from typing import Any

from bolinette.core import Cache, CoreSection, meta
from bolinette.core.injection import Injection, ScopedInjection, post_init
from bolinette.core.logging import Logger
from bolinette.core.mapping import Mapper
from bolinette.core.types import Function, Type, TypeChecker, TypeVarLookup
from bolinette.core.utils import AttributeUtils
from bolinette.web.abstract import Request, Response, ResponseState
from bolinette.web.auth import AuthProviders, BolinetteAuthProvider
from bolinette.web.config import BlntAuthProps, WebConfig
from bolinette.web.controller import Controller, ControllerMeta
from bolinette.web.exceptions import (
    MethodNotAllowedDispatchError,
    NotFoundDispatchError,
    WebErrorHandler,
)
from bolinette.web.middleware import Middleware, MiddlewareBag
from bolinette.web.resources import (
    HttpHeaders,
    ResponseData,
    ResponseWriter,
    RouteParamArgResolver,
    RoutePayloadArgResolver,
)
from bolinette.web.routing import Route, RouteBucket, Router
from bolinette.web.ws import WebSocketHandler


class WebResources:
    def __init__(
        self,
        inject: Injection,
        logger: "Logger[WebResources]",
        core_section: CoreSection,
        checker: TypeChecker,
    ) -> None:
        self.inject = inject
        self.logger = logger
        self.core_section = core_section
        self.checker = checker
        self.router = Router()

    @post_init
    def _init_blnt_auth(self, config: WebConfig, providers: AuthProviders, inject: Injection) -> None:
        if config.blnt_auth is not None:
            inject.add_singleton(BlntAuthProps, instance=config.blnt_auth)
            providers.add_provider(BolinetteAuthProvider)

    @post_init
    def _init_sockets(self, config: WebConfig, inject: Injection) -> None:
        if config.use_sockets:
            inject.add_singleton(WebSocketHandler)

    @post_init
    def _init_ctrls(self, cache: Cache) -> None:
        for ctrl_cls in cache.get(ControllerMeta, hint=type[Controller], raises=False):
            ctrl_meta = meta.get(ctrl_cls, ControllerMeta)
            attr: Any
            for attr in AttributeUtils.get_cls_attrs(ctrl_cls).values():
                if not meta.has(attr, RouteBucket):
                    continue
                bucket = meta.get(attr, RouteBucket)
                for props in bucket.routes:
                    self.add_route(ctrl_cls, ctrl_meta.path, attr, props.method, props.path)

    def add_route(
        self,
        ctrl_cls: type[Controller],
        controller_path: str,
        route_func: Callable[..., Any],
        method: str,
        route_path: str,
    ) -> None:
        if not route_path.startswith("/"):
            route_path = "/".join(p for p in [controller_path.removesuffix("/"), route_path] if p)
        if not route_path.startswith("/"):
            route_path = f"/{route_path}"
        self.router.add_route(Route(method, route_path, Type(ctrl_cls), Function(route_func)))

    async def dispatch(self, request: Request, response: Response) -> None:
        result: object | None = None
        data: ResponseData | None = None
        try:
            route = self.router.dispatch(request)
            await self._handle_request(route, request, response)
        except NotFoundDispatchError:
            result = "404 Not Found"
            data = ResponseData(status=HTTPStatus.NOT_FOUND, headers={HttpHeaders.ContentType: "text/plain"})
        except MethodNotAllowedDispatchError:
            result = "405 Method Not Allowed"
            data = ResponseData(status=HTTPStatus.METHOD_NOT_ALLOWED, headers={HttpHeaders.ContentType: "text/plain"})
        if result is not None and data is not None:
            if response.state != ResponseState.Idle:
                self.logger.error("Response has already started, unable to send error")
            else:
                writer = ResponseWriter(self.inject, response)
                await writer.write_result(result, data)
                await writer.close()

    @staticmethod
    def _prepare_session(inject: Injection, request: Request, data: ResponseData) -> None:
        inject.add_scoped(Request, instance=request)
        inject.add_scoped(ResponseData, instance=data)

    async def _handle_request(
        self,
        route: Route[..., Any],
        request: Request,
        response: Response,
    ) -> None:
        self.logger.info(f"Received request on {request.path}")
        writer = ResponseWriter(self.inject, response)
        try:
            async with self.inject.get_async_scoped_session() as scoped_inject:
                data = ResponseData()
                self._prepare_session(scoped_inject, request, data)
                mdlws = self._collect_middlewares(route, scoped_inject)
                result = await self._middleware_chain(route, request, scoped_inject, mdlws)
                await writer.write_result(result, data)
        except Exception as err:
            status, content = WebErrorHandler.create_error_payload(err, self.core_section.debug)
            if status == 500:
                self.logger.error(str(type(err)), exc_info=err)
            else:
                self.logger.error(str(type(err)))
            if response.state != ResponseState.Idle:
                self.logger.error("Response has already started, unable to send error")
            else:
                await writer.write_result(
                    content,
                    ResponseData(
                        status=status,
                        headers={HttpHeaders.ContentType: "application/json"},
                    ),
                )
        finally:
            await writer.close()

    async def _middleware_chain(
        self,
        route: Route[..., Any],
        request: Request,
        scoped: ScopedInjection,
        mdlws: list[Middleware[Any]],
        index: int = 0,
    ) -> Any:
        async def _next_handle() -> Any:
            return await self._middleware_chain(route, request, scoped, mdlws, index + 1)

        if index >= len(mdlws):
            return await self._call_controller(route, request, scoped)
        else:
            mdlw = mdlws[index]
            self.logger.debug(f"Calling middleware {mdlw.__class__.__qualname__}")
            return await scoped.call(mdlw.handle, args=[_next_handle])

    async def _call_controller(
        self,
        route: Route[..., Any],
        request: Request,
        scoped: Injection,
    ) -> Any:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            body = None
        ctrl = scoped.instantiate(route.controller.cls)
        self.logger.debug(f"Calling controller route {route.func}(...)")
        return scoped.call(
            route.func.func,
            args=[ctrl],
            additional_resolvers=[
                RouteParamArgResolver(route, request),
                RoutePayloadArgResolver(route, scoped.require(Mapper), body),
            ],
            vars_lookup=TypeVarLookup(route.controller),
        )

    @staticmethod
    def _collect_middlewares(route: Route[..., Any], scoped: Injection) -> list[Middleware[Any]]:
        bags: list[MiddlewareBag] = []
        if meta.has(route.controller.cls, MiddlewareBag):
            bags.append(meta.get(route.controller.cls, MiddlewareBag))
        if meta.has(route.func, MiddlewareBag):
            bags.append(meta.get(route.func, MiddlewareBag))
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
