from typing import Dict

import aiohttp_cors
from aiohttp import web as aio_web
from aiohttp.web_request import Request
from aiohttp.web_urldispatcher import Resource, ResourceRoute

from bolinette import core, blnt, types
from bolinette.exceptions import APIError, ForbiddenError
from bolinette.utils import Pagination, response
from bolinette.utils.serializing import deserialize, serialize


class BolinetteResources:
    def __init__(self, context: 'core.BolinetteContext'):
        self.context = context
        self._resources: Dict[str, 'BolinetteResource'] = {}
        self.cors = aiohttp_cors.setup(self.context.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

    def add_route(self, path: str, controller: 'blnt.Controller', route: 'blnt.ControllerRoute'):
        if path not in self._resources:
            self._resources[path] = BolinetteResource(self.cors.add(self.context.app.router.add_resource(path)))
        handler = RouteHandler(controller, route)
        self._resources[path].routes[route.method] = self.cors.add(
            self._resources[path].resource.add_route(route.method.http_verb, handler))


class BolinetteResource:
    def __init__(self, resource: Resource):
        self.resource = resource
        self.routes: Dict[types.web.HttpMethod, ResourceRoute] = {}


class RouteHandler:
    def __init__(self, controller: 'blnt.Controller', route: 'blnt.ControllerRoute'):
        self.controller = controller
        self.route = route

    async def __call__(self, request: Request):
        context: core.BolinetteContext = request.app['blnt']
        user_service = context.service('user')
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
                if self.route.access is not None:
                    current_user = await user_service.get_by_username(self.route.access.check(context, request),
                                                                      safe=True)

                if self.route.roles and len(self.route.roles):
                    user_roles = set(map(lambda r: r.name, current_user.roles))
                    if 'root' not in user_roles and not len(user_roles.intersection(set(self.route.roles))):
                        raise ForbiddenError(f'user.forbidden:{",".join(self.route.roles)}')

                if self.route.expects is not None:
                    exp_def = context.mapping.payload(self.route.expects.model, self.route.expects.key)
                    payload = context.mapping.validate_payload(exp_def, payload, self.route.expects.patch)
                    await context.mapping.link_foreign_entities(exp_def, payload)

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

            if self.route.returns is not None:
                ret_def = context.mapping.response(self.route.returns.model, self.route.returns.key)
                if content.get('data') is not None:
                    content['data'] = context.mapping.marshall(ret_def, content['data'],
                                                               skip_none=self.route.returns.skip_none,
                                                               as_list=self.route.returns.as_list)

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
