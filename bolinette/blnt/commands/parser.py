import asyncio
import inspect
import sys
from argparse import ArgumentParser

import bolinette
from bolinette import Console
from bolinette.exceptions import InitError
from bolinette.blnt.commands import Command, Argument
from bolinette.utils.functions import async_invoke, invoke


class Parser:
    def __init__(self, blnt: 'bolinette.Bolinette', commands: dict[str, Command], anonymous: bool):
        self.blnt = blnt
        self.commands = commands
        self._anonymous = anonymous
        self._factories = {
            'argument': self._create_argument,
            'option': self._create_option,
            'flag': self._create_flag
        }
        self._console = Console()
        self._sub_commands = {}

    def run(self):
        tree = self._parse_commands()
        parser = ArgumentParser(description='Bolinette Web Framework')
        sub_parsers = parser.add_subparsers()
        self._build_parsers(tree, sub_parsers, [])
        parsed = vars(parser.parse_args())
        if '__blnt_cmd__' in parsed:
            cmd = parsed.pop('__blnt_cmd__')
            self._run_command(cmd, parsed)
        elif '__blnt_path__' in parsed:
            self._console.error(self._sub_commands[parsed['__blnt_path__']].format_help())
            sys.exit(1)
        else:
            self._console.error(parser.format_help())
            sys.exit(1)

    def _run_command(self, cmd: str, parsed: dict):
        command = self.commands[cmd]
        if self._anonymous and not command.allow_anonymous:
            self.blnt.context.logger.error(
                'No Bolinette app found! Please do the following:\n'
                '  - Use the CLI at top level of your Bolinette web app\n'
                '  - Make sure manifest.blnt.yaml has the correct module attribute\n'
                '  - Make sure to expose a @main_func decorated function that returns a Bolinette instance '
                'in the top package __init__.py file'
            )
            sys.exit(1)
        func = command.func
        if command.run_init:
            self.blnt.init_bolinette()
        if inspect.iscoroutinefunction(func):
            asyncio.run(async_invoke(func, self.blnt.context, **parsed))
        else:
            invoke(func, self.blnt.context, **parsed)

    def _parse_commands(self):
        command_tree = {}
        for _, command in self.commands.items():
            cur_node = command_tree
            path = command.path.split(' ')
            for elem in path[:-1]:
                if elem not in cur_node:
                    cur_node[elem] = {}
                cur_node = cur_node[elem]
            elem = path[-1]
            if elem in cur_node:
                raise InitError(f'Conflict with "{command.name}" command')
            cur_node[elem] = command
        return command_tree

    def _build_parsers(self, command_tree: dict, sub_parsers, path: list[str]):
        for name, elem in command_tree.items():
            if isinstance(elem, Command):
                sub_parser = sub_parsers.add_parser(name, help=elem.summary)
                for arg in elem.args:
                    self._factories[arg.arg_type](arg, sub_parser)
                sub_parser.set_defaults(__blnt_cmd__=elem.name)
            else:
                sub_parser = sub_parsers.add_parser(name, help=self._build_help(elem, path + [name]))
                sub_parser.set_defaults(__blnt_path__=name)
                self._sub_commands[name] = sub_parser
                self._build_parsers(elem, sub_parser.add_subparsers(), path + [name])

    @staticmethod
    def _build_help(command_tree: dict, path: list[str]):
        commands = [f'"{" ".join(path + [x])}"' for x in command_tree]
        return 'Sub-commands: ' + ', '.join(commands)

    @staticmethod
    def _create_parser_arg(arg: Argument, *, optional: bool = False, use_flag: bool = False,
                           action: str = None):
        args = []
        kwargs = {}
        if optional:
            args.append(f'--{arg.name}')
        else:
            args.append(arg.name)
        if use_flag and arg.flag is not None:
            args.append(f'-{arg.flag}')
        if arg.summary is not None:
            kwargs['help'] = arg.summary
        if action is not None:
            kwargs['action'] = action
        if arg.value_type is not None:
            kwargs['type'] = arg.value_type
        return args, kwargs

    @staticmethod
    def _create_argument(arg: Argument, parser: ArgumentParser):
        args, kwargs = Parser._create_parser_arg(arg, optional=False, use_flag=False, action=None)
        parser.add_argument(*args, **kwargs)

    @staticmethod
    def _create_option(arg: Argument, parser: ArgumentParser):
        args, kwargs = Parser._create_parser_arg(arg, optional=True, use_flag=True, action=None)
        parser.add_argument(*args, **kwargs)

    @staticmethod
    def _create_flag(arg: Argument, parser: ArgumentParser):
        args, kwargs = Parser._create_parser_arg(arg, optional=True, use_flag=True, action='store_true')
        parser.add_argument(*args, **kwargs)
