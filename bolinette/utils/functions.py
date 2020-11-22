import inspect
from typing import Callable, Awaitable, Any

from bolinette.exceptions import InternalError


def _parse_params(function, *args, **kwargs):
    cur_arg = 0
    func_params = {}
    for key, param in inspect.signature(function).parameters.items():
        if param.kind == param.VAR_KEYWORD:
            for name, value in kwargs.items():
                if name not in func_params:
                    func_params[name] = value
        elif param.kind in [param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD] and cur_arg < len(args):
            func_params[key] = args[cur_arg]
            cur_arg += 1
        elif key in kwargs:
            func_params[key] = kwargs[key]
        else:
            func_params[key] = None
    return func_params


async def async_invoke(function: Callable[[Any], Awaitable[Any]], *args, **kwargs):
    if inspect.iscoroutinefunction(function):
        return await function(**_parse_params(function, *args, **kwargs))
    raise InternalError(f'internal.not_async_function:{function.__name__}')


def invoke(function: Callable[[Any], Any], *args, **kwargs):
    if inspect.isfunction(function):
        return function(**_parse_params(function, *args, **kwargs))
    raise InternalError(f'internal.not_function:{function.__name__}')


def getattr_(entity, key, default):
    if isinstance(entity, dict):
        return entity.get(key, default)
    return getattr(entity, key, default)


def hasattr_(entity, key):
    if isinstance(entity, dict):
        return key in entity
    return hasattr(entity, key)


def setattr_(entity, key, value):
    if isinstance(entity, dict):
        entity[key] = value
    else:
        setattr(entity, key, value)
