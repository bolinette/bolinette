import asyncio
import inspect
import sys
from argparse import ArgumentParser
from typing import Dict

import bolinette
from bolinette import Console
from bolinette.blnt.commands import Command, Argument
from bolinette.utils.functions import async_invoke, invoke


class Parser:
    def __init__(self, blnt: 'bolinette.Bolinette', commands: Dict[str, Command]):
        self.blnt = blnt
        self.commands = commands
        self._factories = {
            'argument': self._create_argument,
            'option': self._create_option,
            'flag': self._create_flag
        }

    def run(self):
        parser = ArgumentParser(description='Bolinette Web Framework')
        sub_parsers = parser.add_subparsers()
        for _, command in self.commands.items():
            sub_parser = sub_parsers.add_parser(command.name, help=command.summary)
            for arg in command.args:
                self._factories[arg.arg_type](arg, sub_parser)
            sub_parser.set_defaults(__blnt__=command.name)
        parsed = vars(parser.parse_args())
        if '__blnt__' not in parsed:
            Console().error('Use the -h option to see CLI usage')
            sys.exit(1)
        cmd = parsed.pop('__blnt__')
        func = self.commands[cmd].func
        parsed['blnt'] = self.blnt
        parsed['context'] = self.blnt.context
        if inspect.iscoroutinefunction(func):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(async_invoke(func, **parsed))
        else:
            invoke(func, **parsed)

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
