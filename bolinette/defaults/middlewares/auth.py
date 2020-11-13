from bolinette import web
from bolinette.decorators import middleware
from bolinette.exceptions import ForbiddenError, UnauthorizedError


@middleware('auth', priority=0, pre_validation=True)
class AuthMiddleware(web.Middleware):
    async def handle(self, request, params, next_func):
        identity = self.context.jwt.verify(request, optional=self.options.get('optional', False),
                                           fresh=self.options.get('fresh', False))
        current_user = None
        if identity is not None:
            current_user = await self.context.service('user').get_by_username(identity)
        if 'roles' in self.options:
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
