from bolinette import web, blnt
from bolinette.decorators import middleware, injected
from bolinette.exceptions import ForbiddenError, UnauthorizedError


@middleware('auth', priority=20)
class AuthMiddleware(web.InternalMiddleware):
    @injected
    def user_service(self, inject: 'blnt.BolinetteInjection'):
        return inject.services.require('user')

    def define_options(self):
        return {
            'optional': self.params.bool(),
            'fresh': self.params.bool(),
            'roles': self.params.list(self.params.string())
        }

    async def handle(self, request, params, next_func):
        identity = self.context.jwt.verify(request, optional=self.options['optional'],
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
