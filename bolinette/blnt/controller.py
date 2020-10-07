from typing import Callable, List, Dict

from bolinette import core, types, blnt
from bolinette.utils import functions


class Controller:
    __blnt__: 'ControllerMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.__props__ = ControllerProps(self)
        self.context = context
        self.response = context.response
        if self.__blnt__.use_service:
            self.defaults = ControllerDefaults(self)

    @property
    def service(self) -> blnt.Service:
        return self.context.service(self.__blnt__.service_name)

    def default_routes(self):
        return []

    def __repr__(self):
        return f'<Controller {self.__blnt__.name} {self.__blnt__.path}>'


class ControllerMetadata:
    def __init__(self, name: str, path: str, use_service: bool, service_name: str, namespace: str):
        self.name = name
        self.path = path
        self.use_service = use_service
        self.service_name = service_name
        self.namespace = namespace


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
    def __init__(self, func: Callable, path: str, method: types.web.HttpMethod,
                 access: types.web.AccessToken = None, expects: 'ControllerExcepts' = None,
                 returns: 'ControllerReturns' = None, roles: List[str] = None):
        self.controller = None
        self.func = func
        self.path = path
        self.method = method
        self.access = access or types.web.AccessToken.Optional
        self.expects = expects
        self.returns = returns
        self.roles = roles or []


class ControllerExcepts:
    def __init__(self, model: str, key: str = 'default', *, patch: bool = False):
        self.model = model
        self.key = key
        self.patch = patch


class ControllerReturns:
    def __init__(self, model: str, key: str = 'default', *, as_list: bool = False, skip_none: bool = False):
        self.model = model
        self.key = key
        self.as_list = as_list
        self.skip_none = skip_none


class ControllerDefaults:
    def __init__(self, controller: Controller):
        self.service: blnt.Service = controller.service

    def get_all(self, returns='default', *, access=None, roles=None):
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
            resp = await functions.async_invoke(controller.service.get_all,
                                                pagination=pagination, roles=roles, **kwargs)
            return controller.response.ok('OK', resp)

        return ControllerRoute(route, '', types.web.HttpMethod.GET, access=access, roles=roles,
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns, as_list=True))

    def get_one(self, returns='default', *, key='id', access=None, roles=None):
        async def route(controller, *, match, **kwargs):
            resp = await functions.async_invoke(controller.service.get_first_by, key, match.get('value'), **kwargs)
            return controller.response.ok('OK', resp)

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.GET, access=access, roles=roles,
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def create(self, returns='default', expects='default', *, access=None, roles=None):
        async def route(controller, payload, **kwargs):
            resp = await functions.async_invoke(controller.service.create, payload, **kwargs)
            return controller.response.created(f'{controller.service.__blnt__.model_name}.created', resp)

        return ControllerRoute(route, '', types.web.HttpMethod.POST, access=access, roles=roles,
                               expects=ControllerExcepts(self.service.__blnt__.model_name, expects),
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def update(self, returns='default', expects='default', *, key='id', access=None, roles=None):
        async def route(controller, payload, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            resp = await functions.async_invoke(controller.service.update, entity, payload, **kwargs)
            return controller.response.ok(f'{controller.service.__blnt__.model_name}.updated', resp)

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.PUT, access=access, roles=roles,
                               expects=ControllerExcepts(self.service.__blnt__.model_name, expects),
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def patch(self, returns='default', expects='default', *, key='id', access=None, roles=None):
        async def route(controller, payload, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            resp = await functions.async_invoke(controller.service.patch, entity, payload, **kwargs)
            return controller.response.ok(f'{controller.service.__blnt__.model_name}.updated', resp)

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.PATCH, access=access, roles=roles,
                               expects=ControllerExcepts(self.service.__blnt__.model_name, expects, patch=True),
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def delete(self, returns='default', *, key='id', access=None, roles=None):
        async def route(controller, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            resp = await functions.async_invoke(controller.service.delete, entity, **kwargs)
            return controller.response.ok(f'{controller.service.__blnt__.model_name}.deleted', resp)

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.DELETE, access=access, roles=roles,
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))
