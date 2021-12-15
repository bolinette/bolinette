import sys
from datetime import datetime
from typing import Any, Callable

from aiohttp import web as aio_web

from bolinette import core, Console
from bolinette.core.commands import Parser, Command
from bolinette.exceptions import InitError
from bolinette.utils import paths


class Bolinette:
    def __init__(self, *, profile: str = None, overrides: dict[str, Any] = None, **kwargs):
        self._anonymous = kwargs.get('_anonymous', False)
        self._start_time = datetime.utcnow()
        try:
            self.context = core.BolinetteContext(paths.dirname(__file__), profile=profile, overrides=overrides)
            self.context['__blnt__'] = self
        except InitError as init_error:
            Console().error(f'Error raised during Bolinette init phase\n{str(init_error)}')
            exit(1)
        self.console = Console(debug=self.context.env.debug)

    async def startup(self, *, for_tests_only: bool = False):
        init_funcs = list(self.context.inject.get_global_instances(core.InitFunction))
        self.console.debug(f'Initializing Bolinette with extensions: TODO, '
                           f'and running {len(init_funcs)} init functions')
        for func in init_funcs:
            if for_tests_only and not func.rerun_for_tests:
                continue
            await func(self.context)

    def start_server(self, *, host: str = None, port: int = None):
        if 'aiohttp' not in self.context:
            self.console.error('The aiohttp server was not initialized. '
                               'Make sure to call the bolinette.startup() coroutine before start_server().')
            sys.exit(1)
        self.console.debug(f'Startup took {int((datetime.utcnow() - self._start_time).microseconds / 1000)}ms')
        self.context.logger.info(f"Starting Bolinette with '{self.context.env['profile']}' environment profile")
        aio_web.run_app(self.context['aiohttp'],
                        host=host or self.context.env['host'],
                        port=port or self.context.env['port'],
                        access_log=self.context.logger)
        self.context.logger.info('Bolinette stopped gracefully')

    def exec_cmd_args(self):
        commands = dict((c.name, c) for c in core.cache.get_instances(Command))
        parser = Parser(self, commands, self._anonymous)
        parser.run()


def main_func(func: Callable[[], Bolinette]):
    setattr(func, '__blnt__', '__blnt_main__')
    return func
