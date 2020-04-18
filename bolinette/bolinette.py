import asyncio
import inspect

from aiohttp import web as aio_web

from bolinette import env, network, bcrypt, db, services, web, ws
from bolinette.commands import commands


class Bolinette:
    def __init__(self, *, profile=None, overrides=None):
        env.init_app(profile=profile, overrides=overrides)
        db.engine.init_app()
        services.init_services()
        network.jwt.init_app()
        bcrypt.init_app()
        web.resources.init_app()
        ws.resources.init_app()

    def run(self):
        aio_web.run_app(web.resources.app)

    @property
    def app(self):
        return web.resources.app

    def run_command(self, name, **kwargs):
        if name in commands.commands:
            func = commands.commands[name]
            if inspect.isfunction(func):
                if inspect.iscoroutinefunction(func):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(func(**kwargs))
                else:
                    func(**kwargs)
