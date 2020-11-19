import asyncio
import inspect

from aiohttp import web as aio_web
from bolinette.utils import paths

from bolinette import blnt, console
from bolinette.commands import commands
from bolinette.exceptions import InitError
from bolinette.utils.functions import invoke


class Bolinette:
    def __init__(self, *, profile=None, overrides=None):
        try:
            self.app = aio_web.Application()
            self.context = blnt.BolinetteContext(paths.dirname(__file__), self.app,
                                                 profile=profile, overrides=overrides)
            self.app['blnt'] = self.context
            self.run_init_functions(self.app)
        except InitError as init_error:
            console.error(f'Error raised during Bolinette init phase\n{str(init_error)}')
            exit(1)

    @staticmethod
    def run_init_functions(app):
        for func in blnt.cache.init_funcs:
            func(app['blnt'])

    def run(self):
        self.context.logger.info(f"Starting Bolinette with '{self.context.env['profile']}' environment profile")
        aio_web.run_app(self.app, port=self.context.env['port'], access_log=self.context.logger)
        self.context.logger.info(f"Bolinette stopped gracefully")

    def run_command(self, *args, **kwargs):
        kwargs['blnt'] = self
        name = args[0]
        kwargs['args'] = args[1:]
        if name in commands.commands:
            func = commands.commands[name]
            if inspect.isfunction(func):
                if inspect.iscoroutinefunction(func):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(func(self.context, **kwargs))
                else:
                    invoke(func, **kwargs)
