from http import HTTPStatus
from typing import Any

from escondite import Cache
from peritype import FWrap, TWrap, wrap_func, wrap_type
from soupape import AsyncInjector

from bolinette.core import Logger, meta
from bolinette.core.configuration import ConfigSection, CoreConfigSection
from bolinette.core.mapping import Mapper
from bolinette.web._abstract import Request, Response, ResponseState
from bolinette.web._controller import Controller, ControllerMeta
from bolinette.web._headers import HttpHeaders
from bolinette.web._middleware import Middleware, MiddlewareBag
from bolinette.web._resources._data import ResponseData
from bolinette.web._resources._writer import ResponseWriter
from bolinette.web._routing import Route, RouteBucket, Router
from bolinette.web._utils import get_cls_attrs, instance_resolver
from bolinette.web.exceptions import MethodNotAllowedDispatchError, NotFoundDispatchError, WebErrorHandler


class WebResources:
    def __init__(
        self,
        cache: Cache,
        injector: AsyncInjector,
        logger: "Logger[WebResources]",
        core_section: ConfigSection[CoreConfigSection],
        mapper: Mapper,
    ) -> None:
        self.injector = injector
        self.logger = logger
        self.core_section = core_section
        self.mapper = mapper
        self.router = Router()
        for ctrl_cls in cache.get(ControllerMeta.KEY, hint=type[Controller], raises=False):
            ctrl_meta: ControllerMeta = meta.get(ctrl_cls, ControllerMeta.KEY)
            self.add_controller(wrap_type(ctrl_cls), ctrl_meta.path)

    def add_controller(self, ctrl: TWrap[Any], path: str) -> None:
        attr: Any
        for attr in get_cls_attrs(ctrl.inner_type).values():
            if not meta.has(attr, RouteBucket.KEY):
                continue
            bucket: RouteBucket = meta.get(attr, RouteBucket.KEY)
            for props in bucket.routes:
                self.add_route(ctrl, path, wrap_func(attr), props.method, props.path)

    def add_route(
        self,
        ctrl: TWrap[Any],
        controller_path: str,
        route_func: FWrap[..., Any],
        method: str,
        route_path: str,
    ) -> None:
        if not route_path.startswith("/"):
            route_path = "/".join(p for p in [controller_path.removesuffix("/"), route_path] if p)
        if not route_path.startswith("/"):
            route_path = f"/{route_path}"
        self.router.add_route(Route(method, route_path, ctrl, route_func))

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
                writer = ResponseWriter(self.injector, self.mapper, response)
                await writer.write_result(result, data)
                await writer.close()

    @staticmethod
    def _prepare_scope(scoped: AsyncInjector, route: Route, request: Request, data: ResponseData) -> None:
        scoped.services.add_scoped(instance_resolver(Request, request))
        scoped.services.add_scoped(instance_resolver(ResponseData, data))
        scoped.services.add_scoped(instance_resolver(Route, route))

    async def _handle_request(self, route: Route, request: Request, response: Response) -> None:
        self.logger.info(f"Received request on {request.path}")
        writer = ResponseWriter(self.injector, self.mapper, response)
        try:
            async with self.injector.get_scoped_injector() as scoped:
                data = ResponseData()
                self._prepare_scope(scoped, route, request, data)
                mdlws = await self._collect_middlewares(route, scoped)
                result = await self._middleware_chain(route, request, scoped, mdlws)
                await writer.write_result(result, data)
        except Exception as err:
            status, content = WebErrorHandler.create_error_payload(err, self.core_section.value.debug)
            if status == 500:
                self.logger.error(str(type(err)), exc_info=err)
            else:
                self.logger.error(str(type(err)))
            if response.state != ResponseState.Idle:
                self.logger.error("Response has already started, unable to send error")
            else:
                await writer.write_result(
                    content,
                    ResponseData(status=status, headers={HttpHeaders.ContentType: "application/json"}),
                )
        finally:
            await writer.close()

    async def _middleware_chain(
        self,
        route: Route,
        request: Request,
        scoped: AsyncInjector,
        mdlws: list[Middleware[Any]],
        index: int = 0,
    ) -> Any:
        async def _next_handle() -> Any:
            return await self._middleware_chain(route, request, scoped, mdlws, index + 1)

        if index >= len(mdlws):
            return await self._call_controller(route, scoped)
        mdlw = mdlws[index]
        self.logger.debug(f"Calling middleware {mdlw.__class__.__qualname__}")
        return await scoped.call(mdlw.handle, positional_args=[_next_handle])

    async def _call_controller(self, route: Route, scoped: AsyncInjector) -> Any:
        ctrl = await scoped.require(route.controller)
        self.logger.debug(f"Calling controller route {route.func}(...)")
        return await scoped.call(route.func, positional_args=[ctrl])

    @staticmethod
    async def _collect_middlewares(route: Route, scoped: AsyncInjector) -> list[Middleware[Any]]:
        bags: list[MiddlewareBag] = []
        if meta.has(route.controller.inner_type, MiddlewareBag.KEY):
            ctrl_bag: MiddlewareBag = meta.get(route.controller.inner_type, MiddlewareBag.KEY)
            bags.append(ctrl_bag)
        if meta.has(route.func.func, MiddlewareBag.KEY):
            route_bag: MiddlewareBag = meta.get(route.func.func, MiddlewareBag.KEY)
            bags.append(route_bag)
        mdlws: dict[TWrap[Any], Middleware[Any]] = {}
        for bag in bags:
            for t, mdlw_meta in reversed(bag.added.items()):
                mdlw: Middleware[Any] = await scoped.require(t)
                mdlw.options(*mdlw_meta.args, **mdlw_meta.kwargs)
                mdlws[t] = mdlw
            for t in bag.removed:
                mdlws.pop(t, None)
        return list(mdlws.values())
