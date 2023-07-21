from typing import Any, Callable

from aiohttp import web

from bolinette.core import Cache, meta
from bolinette.core.injection import Injection, init_method
from bolinette.core.injection.resolver import ArgResolverOptions
from bolinette.core.types import Type
from bolinette.core.utils import AttributeUtils
from bolinette.web import Controller
from bolinette.web.controller import ControllerMeta
from bolinette.web.middleware import Middleware, MiddlewareBag
from bolinette.web.route import RouteBucket, RouteProps


class WebResources:
    def __init__(self) -> None:
        self.web_app = web.Application()

    @init_method
    def _init_ctrls(self, cache: Cache, inject: Injection) -> None:
        routes: list[web.RouteDef] = []
        for ctrl_cls in cache.get(ControllerMeta, hint=type[Controller]):
            ctrl_meta = meta.get(ctrl_cls, ControllerMeta)
            attr: Any
            for attr in AttributeUtils.get_cls_attrs(ctrl_cls).values():
                if not meta.has(attr, RouteBucket):
                    continue
                bucket = meta.get(attr, RouteBucket)
                for props in bucket.routes:
                    path = props.anon_path
                    if not path:
                        path = ctrl_meta.path
                    elif not path.startswith("/"):
                        path = f"{ctrl_meta.path}/{path}"
                    if path and not path.startswith("/"):
                        path = f"/{path}"
                    match props.method:
                        case "GET":
                            handler = web.get
                        case "POST":
                            handler = web.post
                        case "PUT":
                            handler = web.put
                        case "PATCH":
                            handler = web.patch
                        case "DELETE":
                            handler = web.delete
                        case _:
                            raise NotImplementedError()
                    routes.append(handler(path, RouteHandler(inject, Type(ctrl_cls), props, attr).handle))
        self.web_app.add_routes(routes)


class RouteHandler:
    __slots__ = ("inject", "ctrl_t", "props", "func")

    def __init__(
        self,
        inject: Injection,
        ctrl_t: Type[Controller],
        props: RouteProps,
        func: Callable[..., Any],
    ) -> None:
        self.inject = inject
        self.ctrl_t = ctrl_t
        self.props = props
        self.func = func

    @staticmethod
    def prepare_session(inject: Injection, request: web.Request) -> None:
        inject.add(web.Request, "scoped", instance=request)

    async def handle(self, request: web.Request) -> web.Response:
        try:
            scoped_inject = self.inject.get_scoped_session()
            self.prepare_session(scoped_inject, request)
            mdlws = self.collect_middlewares(scoped_inject)
            return await self.middleware_chain(request, scoped_inject, mdlws, 0)
        except BaseException as e:
            raise e

    async def middleware_chain(
        self,
        request: web.Request,
        scoped: Injection,
        mdlws: list[Middleware[Any]],
        index: int,
    ) -> web.Response:
        async def _next_handle() -> web.Response:
            return await self.middleware_chain(request, scoped, mdlws, index + 1)

        if index >= len(mdlws):
            ctrl = scoped.instanciate(self.ctrl_t.cls)
            return await scoped.call(
                self.func,
                args=[ctrl],
                additional_resolvers=[RouteParamArgResolver(request, self.props)],
            )
        else:
            mdlw = mdlws[index]
            return await scoped.call(mdlw.handle, args=[_next_handle])

    def collect_middlewares(self, scoped: Injection) -> list[Middleware[Any]]:
        bags: list[MiddlewareBag] = []
        if meta.has(self.ctrl_t.cls, MiddlewareBag):
            bags.append(meta.get(self.ctrl_t.cls, MiddlewareBag))
        if meta.has(self.func, MiddlewareBag):
            bags.append(meta.get(self.func, MiddlewareBag))
        mdlws: dict[Type[Middleware[...]], Middleware[...]] = {}
        for bag in bags:
            for t, mdlw_meta in reversed(bag.added.items()):
                mdlw = scoped.instanciate(t.cls)
                mdlw.options(*mdlw_meta.args, **mdlw_meta.kwargs)
                mdlws[t] = mdlw
            for t in bag.removed:
                if t in mdlws:
                    del mdlws[t]
        return list(mdlws.values())


class RouteParamArgResolver:
    def __init__(self, request: web.Request, props: RouteProps) -> None:
        self.request = request
        self.props = props

    def supports(self, options: ArgResolverOptions):
        return (
            options.name in self.props.func_to_url_args
            and self.props.func_to_url_args[options.name] in self.request.match_info
        )

    def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
        value = self.request.match_info[self.props.func_to_url_args[options.name]]
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
