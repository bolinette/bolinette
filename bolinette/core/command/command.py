from collections.abc import Callable
from typing import Any, Awaitable, Literal, ParamSpec

from bolinette.core import Cache, __user_cache__, meta

P_Func = ParamSpec("P_Func")


class CommandMeta:
    def __init__(
        self,
        path: str,
        summary: str,
    ):
        self.path = path
        self.summary = summary


class Argument:
    def __init__(
        self,
        arg_type: Literal["argument", "option", "flag", "count"],
        name: str,
        *,
        flag: str | None = None,
        summary: str | None = None,
        value_type: type[Any] | None = None,
        default: Any | None = None,
        choices: list[str] | None = None,
    ):
        self.arg_type = arg_type
        self.name = name
        self.flag = flag
        self.summary = summary
        self.value_type = value_type
        self.default = default
        self.choices = choices


class ArgumentMeta(list[Argument]):
    pass


class _CommandDecorator:
    def __call__(self, name: str, summary: str, *, cache: Cache | None = None):
        def decorator(func: Callable[P_Func, Awaitable[None]]) -> Callable[P_Func, Awaitable[None]]:
            meta.set(func, CommandMeta(name, summary))
            (cache or __user_cache__).add(CommandMeta, func)
            return func

        return decorator

    def argument(
        self,
        arg_type: Literal["argument", "option", "flag", "count"],
        name: str,
        *,
        flag: str | None = None,
        summary: str | None = None,
        value_type: type | None = None,
        default: Any = None,
        choices: list[str] | None = None,
    ):
        def decorator(func: Callable[P_Func, Awaitable[None]]) -> Callable[P_Func, Awaitable[None]]:
            if not meta.has(func, ArgumentMeta):
                meta.set(func, ArgumentMeta())
            meta.get(func, ArgumentMeta).append(
                Argument(
                    arg_type,
                    name,
                    flag=flag,
                    summary=summary,
                    value_type=value_type,
                    default=default,
                    choices=choices,
                )
            )
            return func

        return decorator


command = _CommandDecorator()
