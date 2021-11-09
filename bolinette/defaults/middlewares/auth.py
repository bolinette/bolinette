from aiohttp.web_request import Request

from bolinette import abc, web
from bolinette.decorators import middleware
from bolinette.exceptions import ForbiddenError, UnauthorizedError
from bolinette.defaults.services import UserService


@middleware('auth', priority=20)
class AuthMiddleware(web.InternalMiddleware):
    def __init__(self, context: abc.Context, user_service: UserService):
        super().__init__(context)
        self.user_service = user_service

    def define_options(self):
        return {
            'optional': self.params.bool(),
            'fresh': self.params.bool(),
            'refresh': self.params.bool(),
            'roles': self.params.list(self.params.string())
        }

    def _get_token(self, request: Request, headers: dict[str, str]) -> str | None:
        location = self.context.env['credentials']
        if location == 'headers':
            return headers.get('BLNT-REFRESH-TOKEN' if self.options['refresh'] else 'BLNT-ACCESS-TOKEN', None)
        return request.cookies.get('refresh_token' if self.options['refresh'] else 'access_token', None)

    async def handle(self, request, params, next_func):
        token = self._get_token(request, params.get('headers', {}))
        identity = self.context.jwt.verify(token, optional=self.options['optional'],
                                           fresh=self.options['fresh'])
        current_user = None
        if identity is not None:
            current_user = await self.user_service.get_by_username(identity)
        if len(self.options['roles']) > 0:
            if current_user is None:
                raise UnauthorizedError('user.unauthorized')
            roles = self.options['roles']
            if isinstance(roles, str):
                roles = [roles]
            if current_user is None:
                raise ForbiddenError(f'user.forbidden:{",".join(roles)}')
            user_roles = set(map(lambda r: r.name, current_user.roles))
            if 'root' not in user_roles and not len(user_roles.intersection(set(roles))):
                raise ForbiddenError(f'user.forbidden:{",".join(roles)}')
        params['current_user'] = current_user
        return await next_func(request, params)
