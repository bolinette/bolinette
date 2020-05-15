from typing import Dict

import aiohttp_cors
from aiohttp import web as aio_web
from aiohttp.web_request import Request
from aiohttp.web_urldispatcher import Resource, ResourceRoute

from bolinette import core, data, types
from bolinette.exceptions import APIError
from bolinette.utils import Pagination
from bolinette.utils.response import response
from bolinette.utils.serializing import deserialize, serialize


class BolinetteResources:
    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context
        self._resources: Dict[str, 'BolinetteResource'] = {}
        self.cors = aiohttp_cors.setup(self.context.app)
        self.cors_default = {
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        }

    def add_route(self, path, controller: 'data.Controller', route: 'data.ControllerRoute'):
        if path not in self._resources:
            self._resources[path] = BolinetteResource(self.cors.add(self.context.app.router.add_resource(path)))
        handler = RouteHandler(controller, route)
        self._resources[path].routes[route.method] = self.cors.add(
            self._resources[path].resource.add_route(route.method.http_verb, handler), self.cors_default)


class BolinetteResource:
    def __init__(self, resource: Resource):
        self.resource = resource
        self.routes: Dict[types.web.HttpMethod, ResourceRoute] = {}


class RouteHandler:
    def __init__(self, controller: 'data.Controller', route: 'data.ControllerRoute'):
        self.controller = controller
        self.route = route

    async def __call__(self, request: Request):
        context: core.BolinetteContext = request.app['blnt']
        current_user = None
        payload = await deserialize(request)
        match = {}
        query = {}
        for key in request.match_info:
            match[key] = request.match_info[key]
        for key in request.query:
            query[key] = request.query[key]
        try:
            with core.Transaction(context):
                resp = await self.route.func(self.controller, payload=payload, match=match,
                                             query=query, current_user=current_user)
            if isinstance(resp, aio_web.Response):
                return resp

            content = resp.content

            if content.get('data') is not None and isinstance(content['data'], Pagination):
                content['pagination'] = {
                    'page': content['data'].page,
                    'per_page': content['data'].per_page,
                    'total': content['data'].total,
                }
                content['data'] = content['data'].items

            # if self.returns is not None:
            #     ret_def = mapping.get_response(self.returns.model, self.returns.key)
            #     if content.get('data') is not None:
            #         content['data'] = mapping.marshall(ret_def, content['data'], skip_none=self.returns.skip_none,
            #                                            as_list=self.returns.as_list)

            serialized, mime = serialize(content, 'application/json')

            web_response = aio_web.Response(text=serialized, status=resp.code, content_type=mime)
            for cookie in resp.cookies:
                if not cookie.delete:
                    web_response.set_cookie(cookie.name, cookie.value,
                                            expires=cookie.expires.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                            path=cookie.path, httponly=cookie.http_only)
                else:
                    web_response.del_cookie(cookie.name, path=cookie.path)

            return web_response
        except APIError as ex:
            res = response.from_exception(ex)
            serialized, mime = serialize(res.content, 'application/json')
            web_response = aio_web.Response(text=serialized, status=res.code, content_type=mime)
            return web_response
