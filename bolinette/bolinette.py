import asyncio
import inspect

from aiohttp import web as aio_web

from bolinette import env, jwt, bcrypt, db
from bolinette.commands import commands
from bolinette.routing import web, resources


class Bolinette:
    def __init__(self, *, profile=None, overrides=None):
        env.init_app(profile=profile, overrides=overrides)
        db.engine.init_app()
        jwt.init_app()
        bcrypt.init_app()
        web.init_app()
        resources.init_app()

    def run(self):
        aio_web.run_app(web.app)

    @property
    def app(self):
        return web.app

    def run_command(self, name, **kwargs):
        if name in commands.commands:
            func = commands.commands[name]
            if inspect.isfunction(func):
                if inspect.iscoroutinefunction(func):
                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(func(**kwargs))
                else:
                    func(**kwargs)
