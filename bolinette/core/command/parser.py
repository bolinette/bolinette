import inspect
import sys
from argparse import Action, ArgumentParser, FileType, Namespace
from collections.abc import Awaitable, Callable, Iterable, Sequence
from typing import Any, Literal, Protocol, override

from bolinette.core import Cache, meta
from bolinette.core.command.command import Argument, CommandMeta
from bolinette.core.exceptions import InitError
from bolinette.core.injection import post_init
from bolinette.core.logging import Logger
from bolinette.core.types import Function, Type


class _SubParsersAction(Protocol):
    def add_parser(self, name: str, *, help: str | None = None) -> ArgumentParser: ...


class Command:
    def __init__(self, func: Function[..., Awaitable[None]], run_startup: bool) -> None:
        self.func = func
        self.run_startup = run_startup


class Parser:
    def __init__(
        self,
        logger: Logger["Parser"],
        cache: Cache,
    ):
        self._cache = cache
        self._logger = logger
        self._commands: dict[str, Command] = {}
        self._sub_commands: dict[str, Any] = {}
        self._parser = ArgumentParser(description="Bolinette Framework")

    @post_init
    def _parse_commands(self) -> None:
        functions = self._cache.get(CommandMeta, hint=Function[..., Awaitable[None]], raises=False)
        commands: dict[str, Command] = {}
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
            command = Command(func, _cmd.run_startup)
            cur_node[elem] = command
            commands[_cmd.path] = command
        self._commands = commands
        self._build_parsers(command_tree, self._parser.add_subparsers(), [])

    def _build_parsers(
        self,
        command_tree: dict[str, dict[str, Any] | Command],
        sub_parsers: _SubParsersAction,
        path: list[str],
    ) -> None:
        sub_commands: dict[str, Any] = {}
        for name, elem in command_tree.items():
            if isinstance(elem, Command) and meta.has(elem.func.func, CommandMeta):
                _cmd = meta.get(elem.func.func, CommandMeta)
                sub_parser = sub_parsers.add_parser(name, help=_cmd.summary)
                annotations = elem.func.annotations()
                for p_name, param in elem.func.parameters().items():
                    if p_name not in annotations:
                        continue
                    param_t: Type[Any] = annotations[p_name]
                    for anno in param_t.annotated:
                        if anno is Argument or isinstance(anno, Argument):
                            if anno is Argument:
                                anno = Argument()
                            flags, kwargs = self._create_argument(
                                elem.func,
                                p_name,
                                param,
                                param_t,
                                anno,  # pyright: ignore[reportArgumentType]
                            )
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
        elif type.cls is bytes:
            kwargs["action"] = BytesArgparserAction
        elif type.cls is bool:
            if "default" in kwargs:
                if kwargs["default"] is False:
                    kwargs["action"] = "store_true"
                else:
                    kwargs["action"] = "store_false"
                del kwargs["default"]
            else:
                kwargs["action"] = "store_true"
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
        elif type.cls is list:
            flags, kwargs = Parser._create_argument(func, p_name, param, Type(type.vars[0]), argument)
            kwargs["action"] = "append"
        else:
            raise InitError(f"Command {func}, Argument '{p_name}', Type {type} is not allowed as a command argument")
        if argument.summary:
            kwargs["help"] = argument.summary
        return flags, kwargs

    def parse_command(self, args: list[str]) -> tuple[Command, dict[str, Any]]:
        parsed = vars(self._parser.parse_args(args))
        if "__blnt_cmd__" in parsed:
            cmd = parsed.pop("__blnt_cmd__")
            if "__blnt_path__" in parsed:
                del parsed["__blnt_path__"]
            return (self._commands[cmd], parsed)
        elif "__blnt_path__" in parsed:
            print(self._sub_commands[parsed["__blnt_path__"]].format_help())
            sys.exit(1)
        else:
            print(self._parser.format_help())
            sys.exit(1)

    @staticmethod
    def _build_help(command_tree: dict[str, Any], path: list[str]):
        commands = [f'"{" ".join([*path, x])}"' for x in command_tree]
        return "Sub-commands: " + ", ".join(commands)


class BytesArgparserAction[_T](Action):
    def __init__(
        self,
        option_strings: Sequence[str],
        dest: str,
        nargs: int | str | None = None,
        const: _T | None = None,
        default: _T | str | None = None,
        type: Callable[[str], _T] | FileType | None = None,
        choices: Iterable[_T] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)

    @override
    def __call__(
        self,
        parser: ArgumentParser,
        namespace: Namespace,
        values: str | Sequence[Any] | None,
        option_string: str | None = None,
    ) -> None:
        if isinstance(values, str):
            setattr(namespace, self.dest, values.encode())
            return
        raise TypeError()
