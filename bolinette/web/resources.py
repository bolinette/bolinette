import traceback
from typing import Dict

import aiohttp_cors
from aiohttp import web as aio_web
from aiohttp.web_request import Request
from aiohttp.web_urldispatcher import Resource, ResourceRoute

from bolinette import console, blnt, web
from bolinette.exceptions import APIError, APIErrors, InternalError, InitError
from bolinette.utils.serializing import serialize


class BolinetteResources:
    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context
        self._resources: Dict[str, 'BolinetteResource'] = {}
        self.cors = aiohttp_cors.setup(self.context.app, defaults=self._setup_cors())

    def _setup_cors(self):
        try:
            conf = {}
            if 'cors' in self.context.env:
                conf = self.context.env['cors']
            if not isinstance(conf, dict):
                raise ValueError()
            defaults = {}
            for site, config in conf.items():
                if not isinstance(config, dict):
                    raise ValueError()
                defaults[site] = aiohttp_cors.ResourceOptions(
                    allow_credentials=config.get('allow_credentials', False),
                    expose_headers=config.get('expose_headers', ()),
                    allow_headers=config.get('allow_headers', ())
                )
            return defaults
        except ValueError:
            raise InitError("""
Invalid CORS config, you should have something like:

cors:
  "*":
    allow_credentials: true
    expose_headers: "*"
    allow_headers: "*"
  "http://client.example.org":
    allow_credentials: true
    expose_headers: "*"
    allow_headers: "*"
    max_age: 3600

See https://github.com/aio-libs/aiohttp-cors for detailed config options
""")

    def add_route(self, path: str, controller: 'web.Controller', route: 'web.ControllerRoute'):
        if path not in self._resources:
            self._resources[path] = BolinetteResource(self.cors.add(self.context.app.router.add_resource(path)))
        handler = RouteHandler(controller, route)
        self._resources[path].routes[route.method] = self.cors.add(
            self._resources[path].resource.add_route(route.method.http_verb, handler.__call__))


class BolinetteResource:
    def __init__(self, resource: Resource):
        self.resource = resource
        self.routes: Dict[web.HttpMethod, ResourceRoute] = {}


class RouteHandler:
    def __init__(self, controller: 'web.Controller', route: 'web.ControllerRoute'):
        self.controller = controller
        self.route = route

    async def __call__(self, request: Request):
        context: blnt.BolinetteContext = request.app['blnt']
        params = {
            'match': {},
            'query': {}
        }
        for key in request.match_info:
            params['match'][key] = request.match_info[key]
        for key in request.query:
            params['query'][key] = request.query[key]

        try:
            track = web.MiddlewareTrack()
            resp = await self.route.call_middleware_chain(request, params, track)
            if not track.done:
                raise InternalError(f'internal.middleware.chain_stopped:{"->".join(track.steps)}')
            return resp
        except (APIError, APIErrors) as ex:
            res = context.response.from_exception(ex)
            if context.env['debug']:
                stack = traceback.format_exc()
                if isinstance(ex, InternalError):
                    console.error(stack)
                res.content['trace'] = stack.split('\n')
            serialized, mime = serialize(res.content, 'application/json')
            web_response = aio_web.Response(text=serialized, status=res.code, content_type=mime)
            return web_response
