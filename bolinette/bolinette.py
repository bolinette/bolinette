import asyncio
import sys
from datetime import datetime
from typing import Dict, Any, List

from aiohttp import web as aio_web

from bolinette import blnt, BolinetteExtension, Extensions, Console
from bolinette.blnt.commands import Parser
from bolinette.exceptions import InitError
from bolinette.utils import paths


class Bolinette:
    def __init__(self, *, extensions: List[BolinetteExtension] = None,
                 profile: str = None, overrides: Dict[str, Any] = None):
        self._start_time = datetime.utcnow()
        self._init = False
        self._init_ext = False
        self.app = None
        try:
            self.context = blnt.BolinetteContext(paths.dirname(__file__), extensions=extensions,
                                                 profile=profile, overrides=overrides)
            self.context.use_extension(Extensions.ALL)
        except InitError as init_error:
            Console().error(f'Error raised during Bolinette init phase\n{str(init_error)}')
            exit(1)
        self.console = Console(debug=self.context.env.debug)

    def _run_init_functions(self):
        index = 0
        for func in blnt.cache.init_funcs:
            if not self.context.has_extension(func.extension):
                continue
            loop = asyncio.get_event_loop()
            if index == 0:
                self.console.debug('Running Bolinette init functions: ', end='')
            else:
                self.console.debug(', ', end='')
            self.console.debug(str(func), end='')
            loop.run_until_complete(func(self.context))
            index += 1
        if index > 0:
            self.console.debug('')

    def init(self, *, force=False):
        if self._init and not force:
            return
        self._run_init_functions()
        self._init = True

    def init_extensions(self, *, force=False):
        if self._init_ext and not force:
            return
        self.app = None
        if self.context.has_extension(Extensions.WEB):
            self._init_web()
        if self.context.has_extension(Extensions.SOCKETS):
            self._init_sockets()
        self._init_ext = True

    def _init_web(self):
        if self.app is None:
            self.app = aio_web.Application()
            self.app['blnt'] = self.context
        self.context.init_web(self.app)

    def _init_sockets(self):
        if self.app is None:
            self.app = aio_web.Application()
            self.app['blnt'] = self.context
        self.context.init_sockets(self.app)

    def start_server(self, *, host: str = None, port: int = None):
        if not self.context.has_extension((Extensions.WEB, Extensions.SOCKETS)):
            self.context.logger.error(f'The web or sockets extensions must be activated to start the aiohttp server!')
            sys.exit(1)
        self.init()
        self.init_extensions()
        if self.context.has_extension(Extensions.WEB):
            if self.context.env['build_docs']:
                self.context.docs.build()
            self.context.docs.setup()
        self.console.debug(f'Startup took {int((datetime.utcnow() - self._start_time).microseconds / 1000)}ms')
        self.context.logger.info(f"Starting Bolinette with '{self.context.env['profile']}' environment profile")
        aio_web.run_app(self.app,
                        host=host or self.context.env['host'],
                        port=port or self.context.env['port'],
                        access_log=self.context.logger)
        self.context.logger.info(f"Bolinette stopped gracefully")

    def use(self, *extensions) -> 'Bolinette':
        self.context.clear_extensions()
        for ext in extensions:
            self.context.use_extension(ext)
        return self

    def exec_cmd_args(self):
        self.init()
        self.init_extensions()
        parser = Parser(self, blnt.cache.commands)
        parser.run()
