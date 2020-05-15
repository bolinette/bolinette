from typing import Type, Callable, List

from bolinette import core, data, types


def model(model_name: str):
    def decorator(model_cls: Type['data.Model']):
        model_cls.__blnt__ = data.ModelMetadata(model_name)
        core.cache.models[model_name] = model_cls
        return model_cls
    return decorator


def model_property(function):
    return data.ModelProperty(function.__name__, function)


def mixin(mixin_name: str):
    def decorator(mixin_cls: Type['data.Mixin']):
        core.cache.mixins[mixin_name] = mixin_cls
        return mixin_cls
    return decorator


def with_mixin(mixin_name: str):
    def decorator(model_cls):
        mixin_cls = core.cache.mixins.get(mixin_name)
        for col_name, col_def in mixin_cls.columns().items():
            setattr(model_cls, col_name, col_def)
        for rel_name, rel_def in mixin_cls.relationships(model_cls).items():
            setattr(model_cls, rel_name, rel_def)
        return model_cls
    return decorator


def init_func(func: Callable[[core.BolinetteContext], None]):
    core.cache.init_funcs.append(func)
    return func


def seeder(func):
    core.cache.seeders.append(func)
    return func


def service(service_name: str, *, model_name: str = None):
    def decorator(service_cls: Type['data.Service']):
        service_cls.__blnt__ = data.ServiceMetadata(service_name, model_name or service_name)
        core.cache.services[service_name] = service_cls
        return service_cls
    return decorator


def controller(controller_name: str, path: str, *, service_name: str = None):
    def decorator(controller_cls: Type['data.Controller']):
        controller_cls.__blnt__ = data.ControllerMetadata(controller_name, path, service_name or controller_name)
        core.cache.controllers[controller_name] = controller_cls
        return controller_cls
    return decorator


def route(path: str, *, method: types.web.HttpMethod, access=None, expects=None, returns=None, roles: List[str] = None):
    def decorator(route_function: Callable):
        return data.ControllerRoute(route_function, path, method, access, expects, returns, roles)
    return decorator


def get(path: str, *, access=None, expects=None, returns=None, roles: List[str] = None):
    return route(path, method=types.web.HttpMethod.GET, access=access, expects=expects, returns=returns, roles=roles)


def post(path: str, *, access=None, expects=None, returns=None, roles: List[str] = None):
    return route(path, method=types.web.HttpMethod.POST, access=access, expects=expects, returns=returns, roles=roles)


def put(path: str, *, access=None, expects=None, returns=None, roles: List[str] = None):
    return route(path, method=types.web.HttpMethod.PUT, access=access, expects=expects, returns=returns, roles=roles)


def patch(path: str, *, access=None, expects=None, returns=None, roles: List[str] = None):
    return route(path, method=types.web.HttpMethod.PATCH, access=access, expects=expects, returns=returns, roles=roles)


def delete(path: str, *, access=None, expects=None, returns=None, roles: List[str] = None):
    return route(path, method=types.web.HttpMethod.DELETE, access=access, expects=expects, returns=returns, roles=roles)
