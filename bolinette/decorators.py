import inspect as _inspect
from collections.abc import Callable, Awaitable
from typing import Literal, Any

from bolinette import abc, blnt, core, web, BolinetteExtension
from bolinette.blnt.commands import Command as _Command, Argument as _Argument


def injected(func: Callable[[Any, abc.inject.Injection], abc.inject.T_Inject], name: str = None):
    return blnt.InjectionProxy(func, name or func.__name__)


def model(model_name: str, *,
          mixins: list[str] = None,
          database: str = 'default',
          model_type: Literal['relational', 'collection'] = 'relational',
          definitions: Literal['ignore', 'append', 'overwrite'] = 'ignore',
          join_table: bool = False):
    def decorator(model_cls: type['core.Model']):
        model_cls.__blnt__ = core.models.ModelMetadata(model_name, database, model_type == 'relational',
                                                       join_table, mixins or [], definitions)
        blnt.cache.models[model_name] = model_cls
        return model_cls
    return decorator


def model_property(function):
    return core.models.ModelProperty(function.__name__, function)


class _MixinDecorator:
    def __call__(self, mixin_name: str):
        def decorator(mixin_cls: type['core.Mixin']):
            blnt.cache.mixins[mixin_name] = mixin_cls
            return mixin_cls
        return decorator

    @staticmethod
    def service_method(func: Callable):
        return core.MixinServiceMethod(func.__name__, func)


mixin = _MixinDecorator()


def init_func(*, extension: BolinetteExtension = None):
    def decorator(func: Callable[['blnt.BolinetteContext'], Awaitable[None]]):
        blnt.cache.init_funcs.append(blnt.InitFunc(func, extension))
        return func
    return decorator


def seeder(func):
    blnt.cache.seeders.append(func)
    return func


def service(service_name: str, *, model_name: str = None):
    def decorator(service_cls: type[core.Service | core.SimpleService]):
        service_cls.__blnt__ = core.ServiceMetadata(service_name, model_name or service_name)
        blnt.cache.services[service_name] = service_cls
        return service_cls
    return decorator


def controller(controller_name: str, path: str | None = None, *,
               namespace: str = '/api', use_service: bool = True,
               service_name: str = None, middlewares: str | list[str] | None = None):
    _path = path if path is not None else f'/{controller_name}'
    _service_name = service_name if service_name is not None else controller_name
    _middlewares = (middlewares if isinstance(middlewares, list)
                    else [middlewares] if isinstance(middlewares, str)
                    else [])

    def decorator(controller_cls: type['web.Controller']):
        controller_cls.__blnt__ = web.ControllerMetadata(
            controller_name, _path, use_service, _service_name, namespace, _middlewares)
        blnt.cache.controllers[controller_name] = controller_cls
        return controller_cls

    return decorator


def route(path: str, *, method: web.HttpMethod, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
          middlewares: str | list[str] | None = None):
    if middlewares is None:
        middlewares = []
    if isinstance(middlewares, str):
        middlewares = [middlewares]

    def decorator(route_function: Callable):
        if (not isinstance(route_function, blnt.InstantiableAttribute)
                and not _inspect.iscoroutinefunction(route_function)):
            raise ValueError(f'Route "{route_function.__name__}" must be an async function')
        if expects is not None and not isinstance(expects, web.Expects):
            raise ValueError(f'Route "{route_function.__name__}": expects argument must be of type web.Expects')
        if returns is not None and not isinstance(returns, web.Returns):
            raise ValueError(f'Route "{route_function.__name__}": expects argument must be of type web.Returns')
        inner_route = None
        if isinstance(route_function, blnt.InstantiableAttribute):
            inner_route = route_function
        docstring = route_function.__doc__
        return blnt.InstantiableAttribute(web.ControllerRoute, dict(
            func=route_function, path=path, method=method, docstring=docstring, expects=expects,
            returns=returns, inner_route=inner_route, middlewares=middlewares
        ))
    return decorator


def get(path: str, *, returns: 'web.Returns' = None,
        middlewares: str | list[str] | None = None):
    return route(path, method=web.HttpMethod.GET, expects=None, returns=returns, middlewares=middlewares)


def post(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
         middlewares: str | list[str] | None = None):
    return route(path, method=web.HttpMethod.POST, expects=expects, returns=returns, middlewares=middlewares)


def put(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
        middlewares: str | list[str] | None = None):
    return route(path, method=web.HttpMethod.PUT, expects=expects, returns=returns, middlewares=middlewares)


def patch(path: str, *, expects: 'web.Expects' = None, returns: 'web.Returns' = None,
          middlewares: str | list[str] | None = None):
    return route(path, method=web.HttpMethod.PATCH, expects=expects, returns=returns, middlewares=middlewares)


def delete(path: str, *, returns: 'web.Returns' = None,
           middlewares: str | list[str] | None = None):
    return route(path, method=web.HttpMethod.DELETE, expects=None, returns=returns, middlewares=middlewares)


def middleware(name: str, *, priority: int = 100, auto_load: bool = False, loadable: bool = True):
    def decorator(middleware_cls: type['web.Middleware']):
        middleware_cls.__blnt__ = web.MiddlewareMetadata(name, priority, auto_load, loadable)
        blnt.cache.middlewares[name] = middleware_cls
        return middleware_cls
    return decorator


def topic(topic_name: str):
    def decorator(topic_cls: type['web.Topic']):
        topic_cls.__blnt__ = web.TopicMetadata(topic_name)
        blnt.cache.topics[topic_name] = topic_cls
        return topic_cls
    return decorator


def channel(rule: str):
    def decorator(channel_function: Callable):
        return web.TopicChannel(channel_function, rule)
    return decorator


class _CommandDecorator:
    @staticmethod
    def _create_command(func):
        return _Command(func.__name__, func)

    def __call__(self, name: str, summary: str, *,
                 run_init: bool = False, allow_anonymous: bool = False):
        def decorator(arg):
            if isinstance(arg, _Command):
                cmd = arg
            elif _inspect.isfunction(arg):
                cmd = self._create_command(arg)
            else:
                raise ValueError('@command must only decorate functions or async functions')
            cmd.init_params(name, summary, run_init, allow_anonymous)
            blnt.cache.commands[cmd.name] = cmd
            return cmd
        return decorator

    def argument(self, arg_type: Literal['argument', 'option', 'flag', 'count'],
                 name: str, *, flag: str = None, summary: str = None,
                 value_type: type = None, default=None, choices: list = None):
        def decorator(arg):
            if isinstance(arg, _Command):
                cmd = arg
            elif _inspect.isfunction(arg):
                cmd = self._create_command(arg)
            else:
                raise ValueError('@command.argument must only decorate function or async functions')
            if arg_type not in ['argument', 'option', 'flag', 'count']:
                raise ValueError(f'Command {cmd.name}: {arg_type} is not a valid argument type')
            cmd.init_args(_Argument(arg_type, name, flag=flag, summary=summary, value_type=value_type,
                                  default=default, choices=choices), *cmd.args)
            return cmd
        return decorator


command = _CommandDecorator()
