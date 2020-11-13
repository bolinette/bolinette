from typing import Type, Callable, List, Union, Tuple

from bolinette import blnt, core, web


def model(model_name: str):
    def decorator(model_cls: Type['core.Model']):
        model_cls.__blnt__ = core.ModelMetadata(model_name)
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


def route(path: str, *, method: web.HttpMethod,
          expects: Union[str, Tuple[str, str]] = None, returns: Union[str, Tuple[str, str]] = None,
          middlewares: Union[str, List[str]] = None):
    if expects is not None:
        if isinstance(expects, tuple):
            expects = web.ControllerExcepts(expects[0], expects[1] if len(expects) > 1 else 'default',
                                            patch='patch' in expects[2:])
        elif isinstance(expects, str):
            expects = web.ControllerExcepts(expects)
    if returns is not None:
        if isinstance(returns, tuple):
            returns = web.ControllerReturns(returns[0], returns[1] if len(returns) > 1 else 'default',
                                            as_list='as_list' in returns[2:], skip_none='skip_none' in returns[2:])
        elif isinstance(returns, str):
            returns = web.ControllerReturns(returns)
    if middlewares is None:
        middlewares = []
    if isinstance(middlewares, str):
        middlewares = [middlewares]

    def decorator(route_function: Callable):
        inner_route = None
        if isinstance(route_function, web.ControllerRoute):
            inner_route = route_function
            route_function = route_function.func
        return web.ControllerRoute(route_function, path, method, expects, returns, inner_route, middlewares)
    return decorator


def get(path: str, *,
        expects: Union[str, Tuple[str, str], Tuple[str, str, str]] = None,
        returns: Union[str, Tuple[str, str]] = None,
        middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.GET, expects=expects, returns=returns, middlewares=middlewares)


def post(path: str, *,
         expects: Union[str, Tuple[str, str], Tuple[str, str, str]] = None,
         returns: Union[str, Tuple[str, str]] = None,
         middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.POST, expects=expects, returns=returns, middlewares=middlewares)


def put(path: str, *,
        returns: Union[str, Tuple[str, str]] = None,
        expects: Union[str, Tuple[str, str], Tuple[str, str, str]] = None,
        middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.PUT, expects=expects, returns=returns, middlewares=middlewares)


def patch(path: str, *,
          expects: Union[str, Tuple[str, str], Tuple[str, str, str]] = None,
          returns: Union[str, Tuple[str, str]] = None,
          middlewares: Union[str, List[str]] = None):
    return route(path, method=web.HttpMethod.PATCH, expects=expects, returns=returns, middlewares=middlewares)


def delete(path: str, *, expects=None, returns=None,
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
