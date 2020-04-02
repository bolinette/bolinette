from aiohttp import web
from aiohttp.web_request import Request

from bolinette import transaction, mapping
from bolinette.exceptions import AbortRequestException, ForbiddenError
from bolinette.routing import deserialize, serialize, AccessType
from bolinette.services import user_service
from bolinette.utils import Pagination


class Route:
    def __init__(self, *, func, base_url, path, method, access, expects, returns, roles):
        self.func = func
        self.base_url = base_url
        self.path = path
        self.method = method
        self.access = access
        self.expects = expects
        self.returns = returns
        self.roles = roles
        if self.roles and len(self.roles) and not self.access:
            self.access = AccessType.Required

    async def handler(self, request: Request):
        route_params = {
            'payload': await deserialize(request),
            'match': {},
            'query': {},
            'current_user': None,
        }
        for key in request.match_info:
            route_params['match'][key] = request.match_info[key]
        for key in request.query:
            route_params['query'][key] = request.query[key]
        try:
            with transaction:
                if self.access is not None:
                    route_params['current_user'] = await user_service.get_by_username(self.access.check(request))

                if self.roles and len(self.roles):
                    current_user = route_params['current_user']
                    user_roles = set(map(lambda r: r.name, current_user.roles))
                    if 'root' not in user_roles and not len(user_roles.intersection(set(self.roles))):
                        raise ForbiddenError(f'user.forbidden:{",".join(self.roles)}')

                if self.expects is not None:
                    def_key = f'{self.expects.model}.{self.expects.key}'
                    exp_def = mapping.get_payload(def_key)
                    route_params['payload'] = mapping.validate_payload(
                        exp_def, route_params['payload'], self.expects.patch)
                    mapping.link_foreign_entities(exp_def, route_params['payload'])

                resp = await self.func(**route_params)

            if isinstance(resp, web.Response):
                return resp

            content = resp.content

            if content.get('data') is not None and isinstance(content['data'], Pagination):
                content['pagination'] = {
                    'page': content['data'].page,
                    'per_page': content['data'].per_page,
                    'total': content['data'].total,
                }
                content['data'] = content['data'].items

            if self.returns is not None:
                def_key = f'{self.returns.model}.{self.returns.key}'
                ret_def = mapping.get_response(def_key)
                if content.get('data') is not None:
                    content['data'] = mapping.marshall(ret_def, content['data'],
                                                       self.returns.skip_none, self.returns.as_list)

            serialized, mime = serialize(content, 'application/json')

            web_response = web.Response(text=serialized, status=resp.code, content_type=mime)
            for cookie in resp.cookies:
                if not cookie.delete:
                    web_response.set_cookie(cookie.name, cookie.value,
                                            expires=cookie.expires.strftime('%a, %d %b %Y %H:%M:%S GMT'),
                                            path=cookie.path, httponly=cookie.http_only)
                else:
                    web_response.del_cookie(cookie.name, path=cookie.path)

            return web_response
        except AbortRequestException as ex:
            serialized, mime = serialize(ex.response.content, 'application/json')
            web_response = web.Response(text=serialized, status=ex.response.code, content_type=mime)
            return web_response

    def __str__(self):
        return f'<Route {self.method.http_verb} {self.base_url}{self.path} >'
