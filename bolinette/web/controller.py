from typing import Callable, List, Dict, Any

from aiohttp.web_request import Request

from bolinette import blnt, core, web
from bolinette.exceptions import InitError
from bolinette.utils import functions


class Controller:
    __blnt__: 'ControllerMetadata' = None

    def __init__(self, context: 'blnt.BolinetteContext'):
        self.__props__ = ControllerProps(self)
        self.context = context
        self.response = context.response
        if self.__blnt__.use_service:
            self.defaults = ControllerDefaults(self)

    @property
    def service(self) -> 'core.Service':
        return self.context.service(self.__blnt__.service_name)

    def default_routes(self):
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


class ControllerProps:
    def __init__(self, controller):
        self.controller = controller

    def _get_attribute_of_type(self, attr_type):
        return dict([(name, attribute)
                     for name, attribute in vars(self.controller.__class__).items()
                     if isinstance(attribute, attr_type)])

    def get_routes(self) -> Dict[str, 'ControllerRoute']:
        return self._get_attribute_of_type(ControllerRoute)


class ControllerRoute:
    def __init__(self, func: Callable, path: str, method: web.HttpMethod,
                 expects: 'Expects' = None, returns: 'Returns' = None,
                 inner_route: 'ControllerRoute' = None, middlewares: List[str] = None):
        self.controller = None
        self.func = func
        self.path = path
        self.method = method
        self.expects = expects
        self.returns = returns
        self.inner_route = inner_route
        self._mdw_defs = middlewares or []
        self.middlewares: List['web.Middleware'] = []

    def init_middlewares(self, context: 'blnt.BolinetteContext', from_controller: List[str], system: List[str]):
        for mdw in system + from_controller + self._mdw_defs:
            self._parse_middleware_options(mdw, context)
        self.middlewares = sorted(sorted(self.middlewares, key=lambda m: m.__blnt__.priority),
                                  key=lambda m: m.__blnt__.pre_validation, reverse=True)

    def _parse_middleware_options(self, mdw: str, context):
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
        for arg in args:
            arg_n, *arg_v = arg.split('=', maxsplit=1)
            arg_n, *filters = arg_n.split(':')
            if len(filters) > 1:
                raise InitError(f'[{self.controller.__class__.__name__}] middleware '
                                f'"{name}|{arg_n}" has too many filters')
            if len(arg_v) == 0:
                value = True
            else:
                value = arg_v[0].split(',')
                if len(value) == 1:
                    value = value[0]
                if len(filters) == 1:
                    value = self._apply_filters(value, filters[0], name, arg_n)
            middleware.options[arg_n] = value
        self.middlewares.append(middleware)

    def _apply_filters(self, value, _filter, mdw, arg):
        if _filter == 'int':
            func = int
        elif _filter == 'float':
            func = float
        else:
            raise InitError(f'[{self.controller.__class__.__name__}] middleware '
                            f'"{mdw}|{arg}": unknown filter "{_filter}"')
        try:
            if isinstance(value, list):
                return [func(v) for v in value]
            return func(value)
        except ValueError:
            raise InitError(f'[{self.controller.__class__.__name__}] middleware '
                            f'"{mdw}|{arg}": unable to parse "{value}" as {_filter}')

    async def call_middleware_chain(self, request: Request, params: Dict[str, Any], track: 'MiddlewareTrack'):
        handles = ([MiddlewareHandle(name=m.__blnt__.name, func=m.handle) for m in self.middlewares]
                   + [MiddlewareHandle('__ctrl_call', self._final_middleware_call)])
        return await self._call_middleware(handles, 0, request, params, track)

    async def _call_middleware(self, handles: List['MiddlewareHandle'], index: int, request: Request,
                               params: Dict[str, Any], track: 'MiddlewareTrack'):
        async def _next(_request, _params):
            return await self._call_middleware(handles, index + 1, _request, _params, track)
        track.append(handles[index].name)
        track.done = handles[index].name == '__ctrl_call'
        return await handles[index].func(request, params, _next)

    async def _final_middleware_call(self, _1, params: Dict[str, Any], _2):
        return await functions.async_invoke(self.func, self.controller, **params)


class MiddlewareHandle:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func


class MiddlewareTrack:
    def __init__(self):
        self.done = False
        self.steps: List[str] = []

    def append(self, step: str):
        self.steps.append(step)


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
        self.service: core.Service = controller.service

    def get_all(self, returns='default', *, middlewares=None):
        async def route(controller, *, query, **kwargs):
            pagination = None
            order_by = []
            if 'page' in query or 'per_page' in query:
                pagination = {
                    'page': int(query.get('page', 0)),
                    'per_page': int(query.get('per_page', 20))
                }
            if 'order_by' in query:
                columns = query['order_by'].split(',')
                for column in columns:
                    order_args = column.split(':')
                    col_name = order_args[0]
                    order_way = order_args[1] if len(order_args) > 1 else 'asc'
                    order_by.append((col_name, order_way == 'asc'))
            resp = await functions.async_invoke(controller.service.get_all, pagination=pagination, **kwargs)
            return controller.response.ok('OK', resp)

        return ControllerRoute(route, '', web.HttpMethod.GET,
                               returns=Returns(self.service.__blnt__.model_name, returns, as_list=True),
                               middlewares=middlewares)

    def get_one(self, returns='default', *, key='id', middlewares=None):
        async def route(controller, *, match, **kwargs):
            resp = await functions.async_invoke(controller.service.get_first_by, key, match.get('value'), **kwargs)
            return controller.response.ok('OK', resp)

        return ControllerRoute(route, '/{value}', web.HttpMethod.GET,
                               returns=Returns(self.service.__blnt__.model_name, returns),
                               middlewares=middlewares)

    def create(self, returns='default', expects='default', *, middlewares=None):
        async def route(controller, payload, **kwargs):
            resp = await functions.async_invoke(controller.service.create, payload, **kwargs)
            return controller.response.created(f'{controller.service.__blnt__.model_name}.created', resp)

        return ControllerRoute(route, '', web.HttpMethod.POST,
                               expects=Expects(self.service.__blnt__.model_name, expects),
                               returns=Returns(self.service.__blnt__.model_name, returns),
                               middlewares=middlewares)

    def update(self, returns='default', expects='default', *, key='id', middlewares=None):
        async def route(controller, payload, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            resp = await functions.async_invoke(controller.service.update, entity, payload, **kwargs)
            return controller.response.ok(f'{controller.service.__blnt__.model_name}.updated', resp)

        return ControllerRoute(route, '/{value}', web.HttpMethod.PUT,
                               expects=Expects(self.service.__blnt__.model_name, expects),
                               returns=Returns(self.service.__blnt__.model_name, returns),
                               middlewares=middlewares)

    def patch(self, returns='default', expects='default', *, key='id', middlewares=None):
        async def route(controller, payload, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            resp = await functions.async_invoke(controller.service.patch, entity, payload, **kwargs)
            return controller.response.ok(f'{controller.service.__blnt__.model_name}.updated', resp)

        return ControllerRoute(route, '/{value}', web.HttpMethod.PATCH,
                               expects=Expects(self.service.__blnt__.model_name, expects, patch=True),
                               returns=Returns(self.service.__blnt__.model_name, returns),
                               middlewares=middlewares)

    def delete(self, returns='default', *, key='id', middlewares=None):
        async def route(controller, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            resp = await functions.async_invoke(controller.service.delete, entity, **kwargs)
            return controller.response.ok(f'{controller.service.__blnt__.model_name}.deleted', resp)

        return ControllerRoute(route, '/{value}', web.HttpMethod.DELETE,
                               returns=Returns(self.service.__blnt__.model_name, returns),
                               middlewares=middlewares)
