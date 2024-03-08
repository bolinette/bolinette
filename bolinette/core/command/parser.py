import inspect
import sys
from argparse import ArgumentParser
from collections.abc import Awaitable, Callable
from typing import Any, Literal, Protocol

from bolinette.core import Cache, Logger, meta
from bolinette.core.command.command import Argument, CommandMeta
from bolinette.core.exceptions import InitError
from bolinette.core.injection import init_method
from bolinette.core.types import Function, Type


class _SubParsersAction(Protocol):
    def add_parser(self, name: str, *, help: str | None = None) -> ArgumentParser: ...


class Parser:
    def __init__(
        self,
        logger: Logger["Parser"],
        cache: Cache,
    ):
        self._cache = cache
        self._logger = logger
        self._commands: dict[str, Function[..., Awaitable[None]]] = {}
        self._sub_commands: dict[str, Any] = {}
        self._parser = ArgumentParser(description="Bolinette Framework")

    @init_method
    def _parse_commands(self) -> None:
        functions = self._cache.get(CommandMeta, hint=Function[..., Awaitable[None]], raises=False)
        commands: dict[str, Function[..., Awaitable[None]]] = {}
        command_tree: dict[str, Any] = {}
        for func in functions:
            _cmd = meta.get(func.func, CommandMeta)
            cur_node = command_tree
            path = _cmd.path.split(" ")
            for elem in path[:-1]:
                if elem not in cur_node:
                    cur_node[elem] = {}
                cur_node = cur_node[elem]
            elem = path[-1]
            if elem in cur_node:
                raise InitError(f"Conflict with '{_cmd.path}' command")
            cur_node[elem] = func
            commands[_cmd.path] = func
        self._commands = commands
        self._build_parsers(command_tree, self._parser.add_subparsers(), [])

    def _build_parsers(
        self,
        command_tree: dict[str, dict[str, Any] | Function[..., Any]],
        sub_parsers: _SubParsersAction,
        path: list[str],
    ) -> None:
        sub_commands: dict[str, Any] = {}
        for name, elem in command_tree.items():
            if isinstance(elem, Function) and meta.has(elem.func, CommandMeta):
                _cmd = meta.get(elem.func, CommandMeta)
                sub_parser = sub_parsers.add_parser(name, help=_cmd.summary)
                annotations = elem.annotations()
                for p_name, param in elem.parameters().items():
                    if p_name not in annotations:
                        continue
                    param_t: Type[Any] = annotations[p_name]
                    for anno in param_t.annotated:
                        if anno is Argument or isinstance(anno, Argument):
                            if anno is Argument:
                                anno = Argument()
                            flags, kwargs = self._create_argument(elem, p_name, param, param_t, anno)
                            sub_parser.add_argument(*flags, **kwargs)
                sub_parser.set_defaults(__blnt_cmd__=_cmd.path)
            elif isinstance(elem, dict):
                sub_parser = sub_parsers.add_parser(name, help=self._build_help(elem, [*path, name]))
                sub_parser.set_defaults(__blnt_path__=name)
                sub_commands[name] = sub_parser
                self._build_parsers(elem, sub_parser.add_subparsers(), [*path, name])
        self._sub_commands = sub_commands

    @staticmethod
    def _create_argument(
        func: Function[..., Any],
        p_name: str,
        param: inspect.Parameter,
        type: Type[Any],
        argument: Argument,
    ) -> tuple[list[str], dict[str, Any]]:
        flags: list[str]
        kwargs: dict[str, Any] = {}
        if param.default != inspect.Signature.empty:
            kwargs["default"] = param.default
        match argument.arg_type:
            case "argument":
                flags = [p_name]
                if type.nullable:
                    raise InitError(f"Command {func}, Argument '{p_name}', A positional argument cannot be nullable")
            case "option":
                flags = [f"--{p_name}"]
                if argument.shorthand:
                    flags.append(f"-{argument.shorthand}")
                if not type.nullable and "default" not in kwargs:
                    kwargs["required"] = True
        if type.cls is str:
            kwargs["type"] = str
        elif type.cls is int:
            kwargs["type"] = int
        elif type.cls is float:
            kwargs["type"] = float
        elif type.cls is Literal:
            if len(type.vars) == 1:
                if type.vars == (True,):
                    kwargs["action"] = "store_true"
                elif type.vars == (False,):
                    kwargs["action"] = "store_false"
                else:
                    kwargs["action"] = "store_const"
                    kwargs["const"] = type.vars[0]
            else:
                if all(isinstance(i, str) for i in type.vars):
                    kwargs["action"] = "store"
                    kwargs["type"] = str
                elif all(isinstance(i, int) for i in type.vars):
                    kwargs["action"] = "store"
                    kwargs["type"] = int
                else:
                    raise InitError(f"Command {func}, Argument '{p_name}', {type} is not a valid argument type")
                kwargs["choices"] = type.vars
        else:
            raise InitError(f"Command {func}, Argument '{p_name}', Type {type} is not allowed as a command argument")
        if argument.summary:
            kwargs["help"] = argument.summary
        return flags, kwargs

    def parse_command(self, args: list[str]) -> tuple[Callable[..., Awaitable[int | None]], dict[str, Any]]:
        parsed = vars(self._parser.parse_args(args))
        if "__blnt_cmd__" in parsed:
            cmd = parsed.pop("__blnt_cmd__")
            if "__blnt_path__" in parsed:
                del parsed["__blnt_path__"]
            return (self._commands[cmd].func, parsed)
        elif "__blnt_path__" in parsed:
            self._logger.error(self._sub_commands[parsed["__blnt_path__"]].format_help())
            sys.exit(1)
        else:
            self._logger.error(self._parser.format_help())
            sys.exit(1)

    @staticmethod
    def _build_help(command_tree: dict[str, Any], path: list[str]):
        commands = [f'"{" ".join([*path, x])}"' for x in command_tree]
        return "Sub-commands: " + ", ".join(commands)
