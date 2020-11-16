import inspect
from typing import Type, Callable, List, Union

from bolinette import blnt, core, web


def model(model_name: str, database: str = 'default'):
    def decorator(model_cls: Type['core.Model']):
        model_cls.__blnt__ = core.ModelMetadata(model_name, database)
        blnt.cache.models[model_name] = model_cls
        return model_cls
    return decorator


def model_property(function):
    return core.ModelProperty(function.__name__, function)


def mixin(mixin_name: str):
    def decorator(mixin_cls: Type['core.Mixin']):
        blnt.cache.mixins[mixin_name] = mixin_cls
        return mixin_cls
    return decorator


def with_mixin(mixin_name: str):
    def decorator(model_cls):
        mixin_cls = blnt.cache.mixins.get(mixin_name)
        for col_name, col_def in mixin_cls.columns().items():
            setattr(model_cls, col_name, col_def)
        for rel_name, rel_def in mixin_cls.relationships(model_cls).items():
            setattr(model_cls, rel_name, rel_def)
        return model_cls
    return decorator


def init_func(func: Callable[['blnt.BolinetteContext'], None]):
    blnt.cache.init_funcs.append(func)
    return func


def seeder(func):
    blnt.cache.seeders.append(func)
    return func


def service(service_name: str, *, model_name: str = None):
    def decorator(service_cls: Type[Union['core.Service', 'core.SimpleService']]):
        service_cls.__blnt__ = core.ServiceMetadata(service_name, model_name or service_name)
        blnt.cache.services[service_name] = service_cls
        return service_cls
    return decorator


def controller(controller_name: str, path: str = None, *,
               namespace: str = '/api', use_service: bool = True,
               service_name: str = None, middlewares: Union[str, List[str]] = None):
    if path is None:
        path = f'/{controller_name}'
    if service_name is None:
        service_name = controller_name
    if middlewares is None:
        middlewares = []
    if isinstance(middlewares, str):
        middlewares = [middlewares]

    def decorator(controller_cls: Type['web.Controller']):
        controller_cls.__blnt__ = web.ControllerMetadata(
            controller_name, path, use_service, service_name, namespace, middlewares)
        blnt.cache.controllers[controller_name] = controller_cls
        return controller_cls
    return decorator


def route(path: str, *, method: web.HttpMethod, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
          middlewares: Union[str, List[str]] = None):
    if middlewares is None:
        middlewares = []
    if isinstance(middlewares, str):
        middlewares = [middlewares]

    def decorator(route_function: Callable):
        if not isinstance(route_function, web.ControllerRoute) and not inspect.iscoroutinefunction(route_function):
            raise ValueError(f'Route "{route_function.__name__}" must be an async function')
        if expects is not None and not isinstance(expects, web.Expects):
            raise ValueError(f'Route "{route_function.__name__}": expects argument must be of type web.Expects')
        if returns is not None and not isinstance(returns, web.Returns):
            raise ValueError(f'Route "{route_function.__name__}": expects argument must be of type web.Returns')
        inner_route = None
        if isinstance(route_function, web.ControllerRoute):
            inner_route = route_function
            route_function = route_function.func
        return web.ControllerRoute(route_function, path, method, expects, returns, inner_route, middlewares)
    return decorator


def get(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
        middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.GET, expects=expects, returns=returns, middlewares=middlewares)


def post(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
         middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.POST, expects=expects, returns=returns, middlewares=middlewares)


def put(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
        middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.PUT, expects=expects, returns=returns, middlewares=middlewares)


def patch(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
          middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.PATCH, expects=expects, returns=returns, middlewares=middlewares)


def delete(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
           middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.DELETE, expects=expects, returns=returns, middlewares=middlewares)


def middleware(name: str, *, priority: int = 10, pre_validation: bool = False):
    def decorator(middleware_cls: Type['web.Middleware']):
        middleware_cls.__blnt__ = web.MiddlewareMetadata(name, min(max(priority, 0), 10), pre_validation)
        blnt.cache.middlewares[name] = middleware_cls
        return middleware_cls
    return decorator


def topic(topic_name: str):
    def decorator(topic_cls: Type['web.Topic']):
        topic_cls.__blnt__ = web.TopicMetadata(topic_name)
        blnt.cache.topics[topic_name] = topic_cls
        return topic_cls
    return decorator


def channel(rule: str):
    def decorator(channel_function: Callable):
        return web.TopicChannel(channel_function, rule)
    return decorator
