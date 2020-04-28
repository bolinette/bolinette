from aiohttp import web as aio_web
from aiohttp.web_request import Request

from bolinette import mapping
from bolinette.exceptions import ForbiddenError, APIError
from bolinette.network import transaction, AccessToken
from bolinette.web import deserialize, serialize, response
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
            self.access = AccessToken.Required

    async def handler(self, request: Request):
        current_user = None
        payload = await deserialize(request)
        match = {}
        query = {}
        for key in request.match_info:
            match[key] = request.match_info[key]
        for key in request.query:
            query[key] = request.query[key]
        try:
            with transaction:
                if self.access is not None:
                    current_user = await user_service.get_by_username(self.access.check(request))

                if self.roles and len(self.roles):
                    user_roles = set(map(lambda r: r.name, current_user.roles))
                    if 'root' not in user_roles and not len(user_roles.intersection(set(self.roles))):
                        raise ForbiddenError(f'user.forbidden:{",".join(self.roles)}')

                if self.expects is not None:
                    exp_def = mapping.get_payload(self.expects.model, self.expects.key)
                    payload = mapping.validate_payload(exp_def, payload, self.expects.patch)
                    mapping.link_foreign_entities(exp_def, payload)

                resp = await self.func(payload=payload, match=match, query=query, current_user=current_user)

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

            if self.returns is not None:
                ret_def = mapping.get_response(self.returns.model, self.returns.key)
                if content.get('data') is not None:
                    content['data'] = mapping.marshall(ret_def, content['data'], skip_none=self.returns.skip_none,
                                                       as_list=self.returns.as_list)

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

    def __str__(self):
        return f'<Route {self.method.http_verb} {self.base_url}{self.path} >'
