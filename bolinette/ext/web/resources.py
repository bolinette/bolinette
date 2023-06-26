from typing import Any, Callable

from aiohttp import web

from bolinette import Cache, meta
from bolinette.ext.web import Controller
from bolinette.ext.web.controller import ControllerMeta
from bolinette.ext.web.route import RouteBucket, RouteProps
from bolinette.injection import Injection, init_method
from bolinette.injection.resolver import ArgResolverOptions
from bolinette.types import Type
from bolinette.utils import AttributeUtils


class WebResources:
    def __init__(self) -> None:
        self.web_app = web.Application()

    @init_method
    def _init_ctrls(self, cache: Cache, inject: Injection) -> None:
        routes: list[web.RouteDef] = []
        for ctrl_cls in cache.get(ControllerMeta, hint=type[Controller]):
            ctrl_meta = meta.get(ctrl_cls, ControllerMeta)
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
        func: Callable,
    ) -> None:
        self.inject = inject
        self.ctrl_t = ctrl_t
        self.props = props
        self.func = func

    async def handle(self, request: web.Request) -> Any:
        try:
            scoped_inject = self.inject.get_scoped_session()
            ctrl = scoped_inject.instanciate(self.ctrl_t.cls)
            return await scoped_inject.call(
                self.func,
                args=[ctrl],
                additional_resolvers=[RouteParamArgResolver(request, self.props)],
            )
        except BaseException:
            pass


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
        return (options.name, value)
