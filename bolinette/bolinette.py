import asyncio
import inspect

from aiohttp import web as aio_web
from bolinette.utils import console, paths

from bolinette import core
from bolinette.commands import commands
from bolinette.exceptions import InitError


class Bolinette:
    def __init__(self, *, profile=None, overrides=None):
        try:
            self.app = aio_web.Application()
            self.context = core.BolinetteContext(paths.dirname(__file__), self.app,
                                                 profile=profile, overrides=overrides)
            self.app['blnt'] = self.context
            self.run_init_functions(self.app)
        except InitError as init_error:
            console.error(f'Error raised during Bolinette init phase\n{str(init_error)}')
            exit(1)

    @staticmethod
    def run_init_functions(app):
        for func in core.cache.init_funcs:
            func(app['blnt'])

    def run(self):
        console.print(f"Starting Bolinette with '{self.context.env['profile']}' environment profile")
        aio_web.run_app(self.app, port=self.context.env['port'])

    def run_command(self, name, **kwargs):
        kwargs['blnt'] = self
        if name in commands.commands:
            func = commands.commands[name]
            if inspect.isfunction(func):
                if inspect.iscoroutinefunction(func):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(func(self.context, **kwargs))
                else:
                    func(**kwargs)
