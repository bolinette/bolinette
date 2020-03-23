from aiohttp import web as aio_web

from bolinette import env, db, jwt, bcrypt
from bolinette.routing import web, resources


class Bolinette:
    def __init__(self, *, profile=None, overrides=None):
        env.init_app(profile=profile, overrides=overrides)
        db.init_app()
        jwt.init_app()
        bcrypt.init_app()
        web.init_app()
        resources.init_app()

    def run(self):
        aio_web.run_app(web.app)
