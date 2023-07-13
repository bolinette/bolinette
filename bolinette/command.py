import sys
from argparse import ArgumentParser
from collections.abc import Callable
from typing import Any, Awaitable, Literal, ParamSpec, Protocol

from bolinette import Cache, Logger, __user_cache__, meta
from bolinette.exceptions import InitError
from bolinette.injection import Injection, init_method

P_Func = ParamSpec("P_Func")


class _SubParsersAction(Protocol):
    def add_parser(self, name: str, *, help: str | None = None) -> ArgumentParser:
        ...


class CommandMeta:
    def __init__(
        self,
        path: str,
        summary: str,
    ):
        self.path = path
        self.summary = summary


class _Argument:
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


class ArgumentMeta(list[_Argument]):
    pass


class Parser:
    def __init__(
        self,
        logger: Logger["Parser"],
        cache: Cache,
        inject: Injection,
    ):
        self._cache = cache
        self._logger = logger
        self._inject = inject
        self._factories = {
            "argument": self._create_argument,
            "option": self._create_option,
            "flag": self._create_flag,
        }
        self._functions: list[Callable[..., Awaitable[None]]] = []
        self._commands: dict[str, Callable[..., Awaitable[None]]] = {}
        self._sub_commands: dict[str, Any] = {}

    @init_method
    def init(self):
        if CommandMeta in self._cache:
            self._functions = self._cache.get(CommandMeta)

    async def run(self) -> None:
        tree = self._parse_commands()
        parser = ArgumentParser(description="Bolinette Framework")
        sub_parsers = parser.add_subparsers()
        self._build_parsers(tree, sub_parsers, [])
        parsed = vars(parser.parse_args())
        if "__blnt_cmd__" in parsed:
            cmd = parsed.pop("__blnt_cmd__")
            if "__blnt_path__" in parsed:
                del parsed["__blnt_path__"]
            await self._run_command(cmd, parsed)
        elif "__blnt_path__" in parsed:
            self._logger.error(self._sub_commands[parsed["__blnt_path__"]].format_help())
            sys.exit(1)
        else:
            self._logger.error(parser.format_help())
            sys.exit(1)

    async def _run_command(self, cmd: str, args: dict[str, Any]):
        await self._inject.call(self._commands[cmd], named_args=args)

    def _parse_commands(self) -> dict[str, Any]:
        command_tree: dict[str, Any] = {}
        for func in self._functions:
            _cmd = meta.get(func, CommandMeta)
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
            self._commands[_cmd.path] = func
        return command_tree

    def _build_parsers(
        self,
        command_tree: dict[str, Any],
        sub_parsers: _SubParsersAction,
        path: list[str],
    ):
        for name, elem in command_tree.items():
            if meta.has(elem, CommandMeta):
                _cmd = meta.get(elem, CommandMeta)
                sub_parser = sub_parsers.add_parser(name, help=_cmd.summary)
                if meta.has(elem, ArgumentMeta):
                    for arg in meta.get(elem, ArgumentMeta):
                        self._factories[arg.arg_type](arg, sub_parser)
                sub_parser.set_defaults(__blnt_cmd__=_cmd.path)
            else:
                sub_parser = sub_parsers.add_parser(name, help=self._build_help(elem, path + [name]))
                sub_parser.set_defaults(__blnt_path__=name)
                self._sub_commands[name] = sub_parser
                self._build_parsers(elem, sub_parser.add_subparsers(), path + [name])

    @staticmethod
    def _build_help(command_tree: dict[str, Any], path: list[str]):
        commands = [f'"{" ".join(path + [x])}"' for x in command_tree]
        return "Sub-commands: " + ", ".join(commands)

    @staticmethod
    def _create_parser_arg(
        arg: _Argument,
        *,
        optional: bool = False,
        use_flag: bool = False,
        action: str | None = None,
    ):
        args: list[Any] = []
        kwargs: dict[str, Any] = {}
        if optional:
            args.append(f"--{arg.name}")
        else:
            args.append(arg.name)
        if use_flag and arg.flag is not None:
            args.append(f"-{arg.flag}")
        if arg.summary is not None:
            kwargs["help"] = arg.summary
        if action is not None:
            kwargs["action"] = action
        if arg.value_type is not None:
            kwargs["type"] = arg.value_type
        return args, kwargs

    @staticmethod
    def _create_argument(arg: _Argument, parser: ArgumentParser):
        args, kwargs = Parser._create_parser_arg(arg, optional=False, use_flag=False, action=None)
        parser.add_argument(*args, **kwargs)

    @staticmethod
    def _create_option(arg: _Argument, parser: ArgumentParser):
        args, kwargs = Parser._create_parser_arg(arg, optional=True, use_flag=True, action=None)
        parser.add_argument(*args, **kwargs)

    @staticmethod
    def _create_flag(arg: _Argument, parser: ArgumentParser):
        args, kwargs = Parser._create_parser_arg(arg, optional=True, use_flag=True, action="store_true")
        parser.add_argument(*args, **kwargs)


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
                _Argument(
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
