from types import SimpleNamespace

from aiohttp import web as aio_web
import aiohttp_cors


class Resources:
    def __init__(self):
        self.app = None
        self.cors = None
        self.routes = []
        self.res = None
        self.cors_default = {
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        }

    def register(self, route):
        self.routes.append(route)

    def init_app(self):
        self.app = aio_web.Application()
        self.cors = aiohttp_cors.setup(self.app)
        self.res = {}
        for route in self.routes:
            path = f'/api{route.base_url}{route.path}'
            method = route.method
            handler = route.handler
            if path not in self.res:
                self.res[path] = SimpleNamespace()
                self.res[path].res = self.cors.add(self.app.router.add_resource(path))
                self.res[path].routes = {}
            self.res[path].routes[method.http_verb] = self.cors.add(
                self.res[path].res.add_route(method.http_verb, handler), self.cors_default)


resources = Resources()
