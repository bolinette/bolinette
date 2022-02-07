from aiohttp import web as aio_web

from bolinette.core import BolinetteContext, InstantiableAttribute
from bolinette.web import ext, WebContext, Controller, ControllerRoute


@ext.init_func()
async def init_controllers(context: BolinetteContext):
    def _init_ctrl(controller: Controller):
        def _init_route(_attr: InstantiableAttribute[ControllerRoute]):
            _route = _attr.instantiate(
                controller=controller,
                context=controller.context,
                web_ctx=controller.web_ctx,
            )
            if _route.inner_route is not None:
                _route.inner_route, _route.func = _init_route(_route.inner_route)  # type: ignore
            return _route, _route.func

        for route_name, proxy in controller.__props__.get_instantiable(ControllerRoute):
            route, _ = _init_route(proxy)
            setattr(controller, route_name, route)
        for _, route in controller.__props__.get_routes():
            route.controller = controller
            route.setup()
        for route in controller.default_routes():
            route.controller = controller
            route.setup()

    for controller_cls in ext.cache.collect_by_type(Controller):
        context.inject.register(
            controller_cls, "controller", controller_cls.__blnt__.name, func=_init_ctrl
        )


@ext.init_func(rerunable=True)
async def init_aiohttp_web(context: BolinetteContext, web_ctx: WebContext):
    aiohttp_app = aio_web.Application()
    context.registry.add(aiohttp_app)
    web_ctx.resources.init_web(aiohttp_app)
    if context.env["build_docs"]:
        web_ctx.docs.build()
    web_ctx.docs.setup()
