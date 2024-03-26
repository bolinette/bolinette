from collections.abc import Awaitable, Callable
from typing import Any, Literal, ParamSpec, overload

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.types import Function

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
    @overload
    def __init__(
        self,
        arg_type: Literal["argument"] = "argument",
        /,
        *,
        default: Any | None = None,
        summary: str | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        arg_type: Literal["option"],
        shorthand: str | None = None,
        /,
        *,
        default: Any | None = None,
        summary: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.arg_type: Literal["argument", "option"]
        self.shorthand: str | None
        match args:
            case ():
                self.arg_type = "argument"
                self.shorthand = None
            case ("argument",):
                self.arg_type = "argument"
                self.shorthand = None
            case ("option",):
                self.arg_type = "option"
                self.shorthand = None
            case ("option", str() as shorthand):
                self.arg_type = "option"
                self.shorthand = shorthand
            case _:
                raise TypeError(Argument.__init__, args)
        self.default: Any | None = kwargs.get("default", None)
        self.summary: str | None = kwargs.get("summary", None)


def command(name: str, summary: str, *, cache: Cache | None = None):
    def decorator(func: Callable[P_Func, Awaitable[int | None]]) -> Callable[P_Func, Awaitable[int | None]]:
        meta.set(func, CommandMeta(name, summary))
        (cache or __user_cache__).add(CommandMeta, Function(func))
        return func

    return decorator
