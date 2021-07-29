import inspect
from collections.abc import Callable, Awaitable
from typing import Any

from bolinette.exceptions import InternalError


def _parse_params(function, *args, **kwargs):
    cur_arg = 0
    arg_cnt = len(args)
    out_args = []
    out_kwargs = {}
    for key, param in inspect.signature(function).parameters.items():
        if param.kind == param.POSITIONAL_ONLY:
            if cur_arg < arg_cnt:
                out_args.append(args[cur_arg])
                cur_arg += 1
            else:
                out_args.append(param.default if not param.empty else None)
        elif param.kind == param.KEYWORD_ONLY:
            out_kwargs[key] = kwargs.pop(key, param.default if not param.empty else None)
        elif param.kind == param.POSITIONAL_OR_KEYWORD:
            if cur_arg < arg_cnt:
                out_args.append(args[cur_arg])
                cur_arg += 1
            else:
                out_args.append(kwargs.pop(key, param.default if not param.empty else None))
        elif param.kind == param.VAR_POSITIONAL:
            while cur_arg < arg_cnt:
                out_args.append(args[cur_arg])
                cur_arg += 1
        elif param.kind == param.VAR_KEYWORD:
            for p_name, p_value in kwargs.items():
                out_kwargs[p_name] = p_value
    return out_args, out_kwargs


async def async_invoke(function: Callable[[Any], Awaitable[Any]], *args, **kwargs):
    if inspect.iscoroutinefunction(function):
        args, kwargs = _parse_params(function, *args, **kwargs)
        return await function(*args, **kwargs)
    raise InternalError(f'internal.not_async_function:{function.__name__}')


def invoke(function: Callable[[Any], Any], *args, **kwargs):
    if inspect.isfunction(function):
        args, kwargs = _parse_params(function, *args, **kwargs)
        return function(*args, **kwargs)
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


def is_db_entity(entity) -> bool:
    return hasattr(entity, '_sa_instance_state')
