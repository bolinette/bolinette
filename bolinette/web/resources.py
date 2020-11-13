from typing import Dict

import aiohttp_cors
from aiohttp import web as aio_web
from aiohttp.web_request import Request
from aiohttp.web_urldispatcher import Resource, ResourceRoute

from bolinette import blnt, web
from bolinette.exceptions import APIError, APIErrors, InternalError
from bolinette.utils import Pagination
from bolinette.utils.serializing import serialize


class BolinetteResources:
    def __init__(self, context: 'blnt.BolinetteContext'):
        self.context = context
        self._resources: Dict[str, 'BolinetteResource'] = {}
        self.cors = aiohttp_cors.setup(self.context.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

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
            serialized, mime = serialize(res.content, 'application/json')
            web_response = aio_web.Response(text=serialized, status=res.code, content_type=mime)
            return web_response
