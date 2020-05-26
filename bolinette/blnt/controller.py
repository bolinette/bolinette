from typing import Callable, List, Dict

from bolinette import core, types, blnt
from bolinette.utils import response


class Controller:
    __blnt__: 'ControllerMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.__props__ = ControllerProps(self)
        self.context = context
        self.defaults = ControllerDefaults(self)

    @property
    def service(self) -> blnt.Service:
        return self.context.service(self.__blnt__.service_name)

    def default_routes(self):
        return []

    def __repr__(self):
        return f'<Controller {self.__blnt__.name} {self.__blnt__.path}>'


class SimpleController:
    __blnt__: 'ControllerMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context
        self.__props__ = ControllerProps(self)

    def __repr__(self):
        return f'<Controller {self.__blnt__.name} {self.__blnt__.path}>'


class ControllerMetadata:
    def __init__(self, name: str, path: str, service_name: str):
        self.name = name
        self.path = path
        self.service_name = service_name


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
        async def route(controller, *, query, **_):
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
            return response.ok('OK', await controller.service.get_all(pagination, order_by))

        return ControllerRoute(route, '', types.web.HttpMethod.GET, access=access, roles=roles,
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns, as_list=True))

    def get_one(self, returns='default', *, key='id', access=None, roles=None):
        async def route(controller, *, match, **_):
            return response.ok('OK', await controller.service.get_first_by(key, match.get('value')))

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.GET, access=access, roles=roles,
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def create(self, returns='default', expects='default', *, access=None, roles=None):
        async def route(controller, *, payload, **kwargs):
            return response.created(f'{controller.service.__blnt__.model_name}.created',
                                    await controller.service.create(payload, **kwargs))

        return ControllerRoute(route, '', types.web.HttpMethod.POST, access=access, roles=roles,
                               expects=ControllerExcepts(self.service.__blnt__.model_name, expects),
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def update(self, returns='default', expects='default', *, key='id', access=None, roles=None):
        async def route(controller, *, match, payload, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            return response.ok(f'{controller.service.__blnt__.model_name}.updated',
                               await controller.service.update(entity, payload, **kwargs))

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.PUT, access=access, roles=roles,
                               expects=ControllerExcepts(self.service.__blnt__.model_name, expects),
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def patch(self, returns='default', expects='default', *, key='id', access=None, roles=None):
        async def route(controller, *, match, payload, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            return response.ok(f'{controller.service.__blnt__.model_name}.updated',
                               await controller.service.patch(entity, payload, **kwargs))

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.PATCH, access=access, roles=roles,
                               expects=ControllerExcepts(self.service.__blnt__.model_name, expects, patch=True),
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))

    def delete(self, returns='default', *, key='id', access=None, roles=None):
        async def route(controller, *, match, **kwargs):
            entity = await controller.service.get_first_by(key, match.get('value'))
            return response.ok(f'{controller.service.__blnt__.model_name}.deleted',
                               await controller.service.delete(entity, **kwargs))

        return ControllerRoute(route, '/{value}', types.web.HttpMethod.DELETE, access=access, roles=roles,
                               returns=ControllerReturns(self.service.__blnt__.model_name, returns))
