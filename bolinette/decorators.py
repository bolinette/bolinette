import inspect as _inspect
from collections.abc import Callable
from typing import Literal, Any

from bolinette.core import (
    abc,
    BolinetteInjection,
    InjectionProxy,
    __global_cache__,
    BolinetteExtension,
)
from bolinette.core.commands import Command as _Command, Argument as _Argument


def injected(
    func: Callable[[Any, BolinetteInjection], abc.T_Instance], name: str = None
):
    return InjectionProxy(func, name or func.__name__)


class _CommandDecorator:
    @staticmethod
    def _create_command(func):
        return _Command(func.__name__, func)

    def __call__(
        self,
        name: str,
        summary: str,
        *,
        exts: list[BolinetteExtension] = None,
        allow_anonymous: bool = False,
    ):
        def decorator(arg):
            if isinstance(arg, _Command):
                cmd = arg
            elif _inspect.isfunction(arg):
                cmd = self._create_command(arg)
            else:
                raise ValueError(
                    "@command must only decorate functions or async functions"
                )
            cmd.init_params(name, summary, exts or [], allow_anonymous)
            __global_cache__.push(cmd, "command", cmd.name)
            return cmd

        return decorator

    def argument(
        self,
        arg_type: Literal["argument", "option", "flag", "count"],
        name: str,
        *,
        flag: str = None,
        summary: str = None,
        value_type: type = None,
        default=None,
        choices: list = None,
    ):
        def decorator(arg):
            if isinstance(arg, _Command):
                cmd = arg
            elif _inspect.isfunction(arg):
                cmd = self._create_command(arg)
            else:
                raise ValueError(
                    "@command.argument must only decorate function or async functions"
                )
            if arg_type not in ["argument", "option", "flag", "count"]:
                raise ValueError(
                    f"Command {cmd.name}: {arg_type} is not a valid argument type"
                )
            cmd.init_args(
                _Argument(
                    arg_type,
                    name,
                    flag=flag,
                    summary=summary,
                    value_type=value_type,
                    default=default,
                    choices=choices,
                ),
                *cmd.args,
            )
            return cmd

        return decorator


command = _CommandDecorator()
