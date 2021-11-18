import asyncio
import sys
from datetime import datetime
from typing import Any, Callable

from aiohttp import web as aio_web

from bolinette import blnt, BolinetteExtension, Extensions, Console
from bolinette.blnt.commands import Parser
from bolinette.exceptions import InitError
from bolinette.utils import paths


class Bolinette:
    def __init__(self, *, extensions: list[BolinetteExtension] = None,
                 profile: str = None, overrides: dict[str, Any] = None, **kwargs):
        self._anonymous = kwargs.get('_anonymous', False)
        self._start_time = datetime.utcnow()
        self._initialized = False
        self.app: aio_web.Application | None = None
        try:
            self.context = blnt.BolinetteContext(paths.dirname(__file__), extensions=extensions,
                                                 profile=profile, overrides=overrides)
            self.context['__blnt__'] = self
            self.context.use_extension(Extensions.ALL)
        except InitError as init_error:
            Console().error(f'Error raised during Bolinette init phase\n{str(init_error)}')
            exit(1)
        self.console = Console(debug=self.context.env.debug)

    def _run_init_functions(self):
        self.console.debug(f'Initializing Bolinette and running {len(blnt.cache.init_funcs)} init functions')
        for func in blnt.cache.init_funcs:
            if not self.context.has_extension(func.extension):
                continue
            asyncio.run(func(self.context))

    def init_bolinette(self):
        self._run_init_functions()
        self.init_extensions()
        self._initialized = True

    def init_extensions(self):
        self.app = None
        if self.context.has_extension(Extensions.WEB):
            self._init_web()
        if self.context.has_extension(Extensions.SOCKETS):
            self._init_sockets()

    def _init_web(self):
        self.console.debug('Initializing web extension')
        if self.app is None:
            self.app = aio_web.Application()
            self.app['blnt'] = self.context
        self.context.init_web(self.app)
        if self.context.env['build_docs']:
            self.context.docs.build()
        self.context.docs.setup()

    def _init_sockets(self):
        self.console.debug('Initializing socket extension')
        if self.app is None:
            self.app = aio_web.Application()
            self.app['blnt'] = self.context
        self.context.init_sockets(self.app)

    def start_server(self, *, host: str = None, port: int = None):
        if not self._initialized:
            self.init_bolinette()
        if not self.context.has_extension((Extensions.WEB, Extensions.SOCKETS)):
            self.context.logger.error(f'The web or sockets extensions must be activated to start the aiohttp server!')
            sys.exit(1)
        self.console.debug(f'Startup took {int((datetime.utcnow() - self._start_time).microseconds / 1000)}ms')
        self.context.logger.info(f"Starting Bolinette with '{self.context.env['profile']}' environment profile")
        aio_web.run_app(self.app,
                        host=host or self.context.env['host'],
                        port=port or self.context.env['port'],
                        access_log=self.context.logger)
        self.context.logger.info('Bolinette stopped gracefully')

    def use(self, *extensions) -> 'Bolinette':
        self.context.clear_extensions()
        for ext in extensions:
            self.context.use_extension(ext)
        return self

    def exec_cmd_args(self):
        parser = Parser(self, blnt.cache.commands, self._anonymous)
        parser.run()


def main_func(func: Callable[[], Bolinette]):
    setattr(func, '__blnt__', '__blnt_main__')
    return func
