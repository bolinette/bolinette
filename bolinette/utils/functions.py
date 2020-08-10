import inspect
from typing import Callable, Awaitable, Any


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
    return func_params


async def async_invoke(function: Callable[[Any], Awaitable[Any]], *args, **kwargs):
    if inspect.iscoroutinefunction(function):
        return await function(**_parse_params(function, *args, **kwargs))
    return None


def invoke(function: Callable[[Any], Any], *args, **kwargs):
    if inspect.isfunction(function):
        return function(**_parse_params(function, *args, **kwargs))
    return None
