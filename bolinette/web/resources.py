import traceback

import aiohttp_cors
from aiohttp import web as aio_web
from aiohttp.web_request import Request
from aiohttp.web_urldispatcher import Resource, ResourceRoute

from bolinette import abc, console, blnt, web
from bolinette.exceptions import APIError, APIErrors, InternalError
from bolinette.utils.serializing import serialize


class BolinetteResources(abc.WithContext):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)
        self._routes: dict[str, dict[web.HttpMethod, web.ControllerRoute]] = {}
        self._aiohttp_resources: dict[str, 'BolinetteResource'] = {}
        self.cors = None

    @property
    def routes(self):
        for path, methods in self._routes.items():
            for method, route in methods.items():
                yield path, method, route

    def _setup_cors(self):
        parsed_conf = {}
        conf = self.context.env.get_all(startswith='cors.')
        for key, value in conf.items():
            keys = key.split('.', maxsplit=2)
            if len(keys) == 3:
                _, site, prop = keys
                if site not in parsed_conf:
                    parsed_conf[site] = {}
                parsed_conf[site][prop] = value
        cors = {}
        for site, conf in parsed_conf.items():
            cors[site] = aiohttp_cors.ResourceOptions(
                allow_credentials=conf.get('allow_credentials', False),
                expose_headers=conf.get('expose_headers', ()),
                allow_headers=conf.get('allow_headers', ()),
                max_age=conf.get('max_age', None),
                allow_methods=conf.get('allow_methods', None),
            )
        return cors

    def init_web(self, app: aio_web.Application):
        for ctrl_cls in self.context.inject.registered(of_type=web.Controller):
            self.context.inject.require(ctrl_cls, immediate=True)
        self._aiohttp_resources = {}
        self.cors = aiohttp_cors.setup(app, defaults=self._setup_cors())
        for path, methods in self._routes.items():
            for method, route in methods.items():
                if path not in self._aiohttp_resources:
                    self._aiohttp_resources[path] = BolinetteResource(
                        self.cors.add(self.context.app.router.add_resource(path)))
                handler = RouteHandler(route)
                self._aiohttp_resources[path].routes[method] = self.cors.add(
                    self._aiohttp_resources[path].resource.add_route(method.http_verb, handler.__call__))

    def add_route(self, path: str, route: 'web.ControllerRoute'):
        if path not in self._routes:
            self._routes[path] = {}
        self._routes[path][route.method] = route


class BolinetteResource:
    def __init__(self, resource: Resource):
        self.resource = resource
        self.routes: dict[web.HttpMethod, ResourceRoute] = {}


class RouteHandler:
    def __init__(self, route: 'web.ControllerRoute'):
        self.controller = route.controller
        self.route = route

    async def __call__(self, request: Request):
        context: blnt.BolinetteContext = request.app['blnt']
        params = {
            'match': {},
            'query': {},
            'request': request
        }
        for key in request.match_info:
            params['match'][key] = request.match_info[key]
        for key in request.query:
            params['query'][key] = request.query[key]
        try:
            resp = await self.route.call_middleware_chain(request, params)
            return resp
        except (APIError, APIErrors) as ex:
            res = web.Response(context).from_exception(ex)
            if context.env['debug']:
                stack = traceback.format_exc()
                if isinstance(ex, InternalError):
                    console.error(stack)
                res.content['trace'] = stack.split('\n')
            serialized, mime = serialize(res.content, 'application/json')
            web_response = aio_web.Response(text=serialized, status=res.code, content_type=mime)
            return web_response
