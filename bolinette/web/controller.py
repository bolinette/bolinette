from typing import Callable, List, Dict, Any, Generator, Optional, Tuple

from aiohttp.web_request import Request

from bolinette import blnt, core, web
from bolinette.exceptions import InitError
from bolinette.utils import functions


class Controller:
    __blnt__: 'ControllerMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.__props__ = ControllerProps(self)
        self.context = context
        self.response = web.Response(context)
        if self.__blnt__.use_service:
            self.defaults = ControllerDefaults(self)

    @property
    def service(self) -> 'core.Service':
        return self.context.service(self.__blnt__.service_name)

    def default_routes(self) -> List['web.ControllerRoute']:
        return []

    def __repr__(self):
        return f'<Controller {self.__blnt__.name} {self.__blnt__.path}>'


class ControllerMetadata:
    def __init__(self, name: str, path: str, use_service: bool, service_name: str,
                 namespace: str, middlewares: List[str]):
        self.name = name
        self.path = path
        self.use_service = use_service
        self.service_name = service_name
        self.namespace = namespace
        self.middlewares = middlewares


class ControllerProps(blnt.Properties):
    def __init__(self, controller):
        super().__init__(controller)

    def get_routes(self) -> Generator[Tuple[str, 'ControllerRoute'], Any, None]:
        return self._get_attributes_of_type(self.parent, ControllerRoute)


class ControllerRoute:
    def __init__(self, controller: 'web.Controller', func: Callable, path: str, method: web.HttpMethod,
                 docstring: Optional[str], expects: 'Expects' = None, returns: 'Returns' = None,
                 inner_route: 'ControllerRoute' = None, middlewares: List[str] = None):
        self.controller = controller
        self.func = func
        self.path = path
        self.method = method
        self.docstring = docstring
        self.expects = expects
        self.returns = returns
        self.inner_route = inner_route
        self._mdw_defs = middlewares or []
        self.middlewares: List['web.Middleware'] = []

    def __repr__(self):
        return f'<Route {self.method.name} "{self.full_path}" {self._mdw_defs}>'

    @property
    def full_path(self):
        return f'{self.controller.__blnt__.namespace}{self.controller.__blnt__.path}{self.path}'

    def setup(self):
        self._init_middlewares(self.controller.context, self.controller.__blnt__.middlewares,
                               self._init_sys_middleware())
        self.controller.context.resources.add_route(self.full_path, self)
        if self.inner_route is not None:
            self.inner_route.setup()

    def _init_middlewares(self, context: 'blnt.BolinetteContext', from_controller: List[str], system: List[str]):
        for mdw in system:
            self._parse_middleware_options(mdw, context, True)
        for mdw in from_controller:
            self._parse_middleware_options(mdw, context)
        for mdw in self._mdw_defs:
            self._parse_middleware_options(mdw, context)
        self.middlewares = sorted(sorted(self.middlewares, key=lambda m: m.__blnt__.priority),
                                  key=lambda m: m.system_priority)

    def _init_sys_middleware(self):
        sys_mdw = [m.__blnt__.name for m in blnt.cache.middlewares.values() if m.__blnt__.auto_load]
        if self.expects is not None:
            model = self.expects.model
            key = self.expects.key if self.expects.key is not None else 'default'
            cmd = f'blnt_payload|model={model}|key={key}'
            if self.expects.patch:
                cmd += '|patch'
            sys_mdw.append(cmd)
        else:
            sys_mdw.append('blnt_payload')
        if self.returns is not None:
            model = self.returns.model
            key = self.returns.key if self.returns.key is not None else 'default'
            cmd = f'blnt_response|model={model}|key={key}'
            if self.returns.as_list:
                cmd += '|as_list'
            if self.returns.skip_none:
                cmd += '|skip_none'
            sys_mdw.append(cmd)
        else:
            sys_mdw.append('blnt_response')
        return sys_mdw

    def _parse_middleware_options(self, mdw: str, context, system: bool = False):
        name, *args = mdw.split('|')
        if name.startswith('!'):
            self.middlewares = list(filter(lambda m: m.__blnt__.name != name[1:], self.middlewares))
            return
        find = list(filter(lambda m: m.__blnt__.name == name, self.middlewares))
        if len(find) > 0:
            middleware = find[0]
            middleware.options = {}
        else:
            middleware = blnt.cache.middlewares[name](context)

        if not middleware.__blnt__.loadable and not system:
            raise InitError(f'[{type(self.controller).__name__}] Middleware '
                            f'"{mdw}" cannot be loaded in a controller')

        parsed_args = {}
        for arg in args:
            arg_n, *arg_v = arg.split('=', maxsplit=1)
            parsed_args[arg_n] = arg_v[0] if len(arg_v) else True
        def_options = middleware.define_options()
        for opt_name, option in def_options.items():
            if opt_name in parsed_args:
                middleware.options[opt_name] = option.validate(parsed_args[opt_name])
            elif option.required:
                raise InitError(f'[{type(self.controller).__name__}] Middleware "{mdw}" '
                                f'option "{opt_name}" is missing from declaration string')
            else:
                middleware.options[opt_name] = option.default
        self.middlewares.append(middleware)

    async def call_middleware_chain(self, request: Request, params: Dict[str, Any]):
        handles = ([MiddlewareHandle(name=m.__blnt__.name, func=m.handle) for m in self.middlewares]
                   + [MiddlewareHandle('__ctrl_call', self._final_middleware_call)])
        return await self._call_middleware(handles, 0, request, params)

    async def _call_middleware(self, handles: List['MiddlewareHandle'], index: int, request: Request,
                               params: Dict[str, Any]):
        async def _next(_request, _params):
            return await self._call_middleware(handles, index + 1, _request, _params)
        return await handles[index].func(request, params, _next)

    async def _final_middleware_call(self, _1, params: Dict[str, Any], _2):
        return await functions.async_invoke(self.func, self.controller, **params)


class MiddlewareHandle:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func


class Expects:
    def __init__(self, model: str, key: str = 'default', *, patch: bool = False):
        self.model = model
        self.key = key
        self.patch = patch


class Returns:
    def __init__(self, model: str, key: str = 'default', *, as_list: bool = False, skip_none: bool = False):
        self.model = model
        self.key = key
        self.as_list = as_list
        self.skip_none = skip_none


class ControllerDefaults:
    def __init__(self, controller: Controller):
        self.controller = controller
        self.service: core.Service = controller.service

    def get_all(self, returns='default', *, prefix='',
                middlewares: List[str] = None, docstring: str = None):
        async def route(controller: web.Controller, **kwargs):
            resp = await functions.async_invoke(controller.service.get_all, **kwargs)
            return controller.response.ok(data=resp)

        model_name = self.service.__blnt__.model_name
        docstring = docstring or f"""
        Gets all records from {model_name} collection

        -response 200 returns: The list of {model_name} entities
        """
        return ControllerRoute(self.controller, route, f'{prefix}', web.HttpMethod.GET, docstring,
                               returns=Returns(model_name, returns, as_list=True),
                               middlewares=middlewares)

    def get_one(self, returns='default', *, key: str = None, prefix='',
                middlewares: List[str] = None, docstring: str = None):
        async def route(controller: web.Controller, *, match, **kwargs):
            resp = await functions.async_invoke(controller.service.get_first_by, key, match.get(key), **kwargs)
            return controller.response.ok(data=resp)

        model_name = self.service.__blnt__.model_name
        key = key or self.service.repo.model.__props__.model_id.name
        docstring = docstring or f"""
        Gets one record from {model_name} collection, identified by {key} field

        -response 200 returns: The {model_name} entity
        """
        return ControllerRoute(self.controller, route, f'{prefix}/{{{key}}}', web.HttpMethod.GET, docstring,
                               returns=Returns(model_name, returns),
                               middlewares=middlewares)

    def create(self, returns='default', expects='default', *, prefix='',
               middlewares: List[str] = None, docstring: str = None):
        async def route(controller: web.Controller, payload, **kwargs):
            resp = await functions.async_invoke(controller.service.create, payload, **kwargs)
            return controller.response.created(messages=f'{controller.service.__blnt__.model_name}.created', data=resp)

        model_name = self.service.__blnt__.model_name
        docstring = docstring or f"""
        Inserts a new entity in {model_name} collection

        -response 201 returns: The created {model_name} entity
        """
        return ControllerRoute(self.controller, route, f'{prefix}', web.HttpMethod.POST, docstring,
                               expects=Expects(self.service.__blnt__.model_name, expects),
                               returns=Returns(model_name, returns),
                               middlewares=middlewares)

    def update(self, returns='default', expects='default', *, key: str = None, prefix='',
               middlewares: List[str] = None, docstring: str = None):
        async def route(controller: web.Controller, payload, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get(key))
            resp = await functions.async_invoke(controller.service.update, entity, payload, **kwargs)
            return controller.response.ok(messages=f'{controller.service.__blnt__.model_name}.updated', data=resp)

        model_name = self.service.__blnt__.model_name
        key = key or self.service.repo.model.__props__.model_id.name
        docstring = docstring or f"""
        Updates all fields from one {model_name} entity, identified by {key} field

        -response 200 returns: The updated {model_name} entity
        """
        return ControllerRoute(self.controller, route, f'{prefix}/{{{key}}}', web.HttpMethod.PUT, docstring,
                               expects=Expects(self.service.__blnt__.model_name, expects),
                               returns=Returns(model_name, returns),
                               middlewares=middlewares)

    def patch(self, returns='default', expects='default', *, key: str = None, prefix='',
              middlewares: List[str] = None, docstring: str = None):
        async def route(controller: web.Controller, payload, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get(key))
            resp = await functions.async_invoke(controller.service.patch, entity, payload, **kwargs)
            return controller.response.ok(messages=f'{controller.service.__blnt__.model_name}.updated', data=resp)

        model_name = self.service.__blnt__.model_name
        key = key or self.service.repo.model.__props__.model_id.name
        docstring = docstring or f"""
        Updates some fields from one {model_name} entity, identified by {key} field

        -response 200 returns: The updated {model_name} entity
        """
        return ControllerRoute(self.controller, route, f'{prefix}/{{{key}}}', web.HttpMethod.PATCH, docstring,
                               expects=Expects(self.service.__blnt__.model_name, expects, patch=True),
                               returns=Returns(model_name, returns),
                               middlewares=middlewares)

    def delete(self, returns='default', *, key: str = None, prefix='',
               middlewares: List[str] = None, docstring: str = None):
        async def route(controller: web.Controller, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get(key))
            resp = await functions.async_invoke(controller.service.delete, entity, **kwargs)
            return controller.response.ok(messages=f'{controller.service.__blnt__.model_name}.deleted', data=resp)

        model_name = self.service.__blnt__.model_name
        key = key or self.service.repo.model.__props__.model_id.name
        docstring = docstring or f"""
        Deletes on record from {model_name} collection, identified by {key} field

        -response 200 returns: The deleted {model_name} entity
        """
        return ControllerRoute(self.controller, route, f'{prefix}/{{{key}}}', web.HttpMethod.DELETE, docstring,
                               returns=Returns(model_name, returns),
                               middlewares=middlewares)
