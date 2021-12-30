import sys
from datetime import datetime
from typing import Any, Callable

from aiohttp import web as aio_web

from bolinette import Console
from bolinette.core import BolinetteExtension, BolinetteContext, __global_cache__
from bolinette.core.commands import Parser, Command
from bolinette.core.extension import BolinetteExtension
from bolinette.exceptions import InitError
from bolinette.utils import paths
from bolinette.utils.functions import async_invoke


class Bolinette:
    def __init__(self, *, profile: str = None, overrides: dict[str, Any] = None, **kwargs):
        self._start_time = datetime.utcnow()
        self._anonymous = kwargs.get('_anonymous', False)
        self._extensions: list[BolinetteExtension] = []
        try:
            self.context = BolinetteContext(paths.dirname(__file__), profile=profile, overrides=overrides)
            self.context.registry.add_singleton(self)
        except InitError as init_error:
            Console().error(f'Error raised during Bolinette init phase\n{str(init_error)}')
            exit(1)
        self.console = Console(debug=self.context.env.debug)

    async def startup(self, *, for_tests_only: bool = False):
        self.console.debug('Initializing Bolinette')
        if not for_tests_only:
            self.context.registry.add_singleton(self.context)
        for ext in self._extensions:
            if not for_tests_only:
                ext_ctx = ext.__create_context__(self.context)
                self.context.registry.add_singleton(ext_ctx)
            else:
                ext_ctx = self.context.registry.get_singleton(ext.__context_type__)
            self.console.debug(f'* Initializing {ext} extension')
            for init_func in ext.init_funcs:
                if for_tests_only and not init_func.rerun_for_tests:
                    continue
                self.console.debug(f'  * Running {init_func} function')
                await async_invoke(init_func.function, self.context, ext_ctx)
        self.console.debug(f'Startup took {int((datetime.utcnow() - self._start_time).microseconds / 1000)}ms')

    def start_server(self, *, host: str = None, port: int = None):
        self.context.logger.info(f"Starting Bolinette with '{self.context.env['profile']}' environment profile")
        aio_web.run_app(self.context.registry.get_singleton(aio_web.Application),
                        host=host or self.context.env['host'],
                        port=port or self.context.env['port'],
                        access_log=self.context.logger)
        self.context.logger.info('Bolinette stopped gracefully')

    def exec_cmd_args(self):
        commands = dict((c.name, c) for c in __global_cache__.get_instances(Command))
        parser = Parser(self, commands, self._anonymous)
        parser.run()

    def load(self, ext: BolinetteExtension):
        for e in ext.dependencies:
            self.load(e)
        if ext in self._extensions:
            raise InitError(f'Extension {ext} is already loaded')
        self._extensions.append(ext)


def main_func(func: Callable[[], Bolinette]):
    setattr(func, '__blnt__', '__blnt_main__')
    return func
