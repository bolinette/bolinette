from typing import Callable, List, Dict

from bolinette import core, types


class Controller:
    __blnt__: 'ControllerMetadata' = None

    def __init__(self, context: 'core.BolinetteContext'):
        self.__props__ = ControllerProps(self)
        self.context = context
        self.service = context.service(self.__blnt__.service_name)

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
    def __init__(self, func: Callable, path: str, method: types.HttpMethod, access, expects, returns, roles: List[str]):
        self.controller = None
        self.func = func
        self.path = path
        self.method = method
        self.access = access
        self.expects = expects
        self.returns = returns
        self.roles = roles
