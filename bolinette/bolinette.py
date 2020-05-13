import asyncio
import inspect

from aiohttp import web as aio_web

from bolinette import env, network, bcrypt, services, web, ws, core
from bolinette.commands import commands


class Bolinette:
    def __init__(self, *, profile=None, overrides=None):
        env.init_app(profile=profile, overrides=overrides)

        self.app = aio_web.Application()
        self.context = core.BolinetteContext()
        self.app['blnt'] = self.context

        self.run_init_functions(self.app)

        services.init_services(self.context)
        network.jwt.init_app()
        bcrypt.init_app()
        web.resources.init_app()
        ws.resources.init_app()

    @staticmethod
    def run_init_functions(app):
        for func in core.cache.init_funcs:
            func(app['blnt'])

    def run(self):
        aio_web.run_app(web.resources.app)

    @property
    def _app(self):
        return web.resources.app

    def run_command(self, name, **kwargs):
        if name in commands.commands:
            func = commands.commands[name]
            if inspect.isfunction(func):
                if inspect.iscoroutinefunction(func):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(func(self.context, **kwargs))
                else:
                    func(**kwargs)
