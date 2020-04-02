from types import SimpleNamespace

import aiohttp_cors

from bolinette.routing import web


class Resources:
    def __init__(self):
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
        self.res = {}
        for route in self.routes:
            path = f'/api{route.base_url}{route.path}'
            method = route.method
            handler = route.handler
            if path not in self.res:
                self.res[path] = SimpleNamespace()
                self.res[path].res = web.cors.add(web.app.router.add_resource(path))
                self.res[path].routes = {}
            self.res[path].routes[method.http_verb] = web.cors.add(
                self.res[path].res.add_route(method.http_verb, handler), self.cors_default)


resources = Resources()
