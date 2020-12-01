import random
import string
from datetime import datetime

from bolinette import blnt, web
from bolinette.decorators import controller, get, post, patch, delete
from bolinette.defaults.services import UserService, RoleService
from bolinette.exceptions import UnprocessableEntityError, EntityNotFoundError


@controller('user', '/user')
class UserController(web.Controller):
    @property
    def user_service(self) -> UserService:
        return self.context.service('user')

    @property
    def role_service(self) -> RoleService:
        return self.context.service('role')

    def default_routes(self):
        return [
            self.defaults.get_all('private', middlewares=['auth|roles=admin']),
            self.defaults.get_one('private', key='username', middlewares=['auth|roles=admin'])
        ]

    def _create_tokens(self, resp, user, *, set_access, set_refresh, fresh):
        now = datetime.utcnow()
        if set_access:
            access_token = self.context.jwt.create_access_token(now, user.username, fresh=fresh)
            resp.cookies.append(web.Cookie('access_token', access_token,
                                           expires=self.context.jwt.access_token_expires(now), path='/'))
        if set_refresh:
            refresh_token = self.context.jwt.create_refresh_token(now, user.username)
            resp.cookies.append(web.Cookie('refresh_token', refresh_token,
                                           expires=self.context.jwt.refresh_token_expires(now),
                                           path='/api/user/refresh'))

    @get('/me', returns=web.Returns('user', 'private'), middlewares=['auth|fresh'])
    async def me(self, current_user):
        return self.response.ok('OK', current_user)

    @get('/info', returns=web.Returns('user', 'private'), middlewares=['auth'])
    async def info(self, current_user):
        return self.response.ok('OK', current_user)

    @post('/login', expects=web.Expects('user', 'login'), returns=web.Returns('user', 'private'))
    async def login(self, payload):
        username = payload['username']
        password = payload['password']
        try:
            user = await self.user_service.get_by_username(username)
        except EntityNotFoundError:
            return self.response.unauthorized('user.login.wrong_credentials')
        if user is not None:
            if self.user_service.check_password(user, password):
                resp = self.response.ok('user.login.success', user)
                self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
                return resp
        return self.response.unauthorized('user.login.wrong_credentials')

    @post('/logout')
    async def logout(self):
        resp = self.response.ok('user.logout.success')
        resp.cookies.append(web.Cookie('access_token', None, delete=True, path='/'))
        resp.cookies.append(web.Cookie('refresh_token', None, delete=True, path='/api/user/refresh'))
        return resp

    @post('/token/refresh', middlewares=['auth'])
    async def refresh(self, current_user):
        resp = self.response.ok('user.token.refreshed')
        self._create_tokens(resp, current_user, set_access=True, set_refresh=False, fresh=False)
        return resp

    @post('/register', expects=web.Expects('user', 'register'), returns=web.Returns('user', 'private'))
    async def register(self, payload):
        if blnt.init.get('ADMIN_REGISTER_ONLY', True):
            raise UnprocessableEntityError('global.register.admin_only')
        user = await self.user_service.create(payload)
        resp = self.response.created('user.registered', user)
        self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
        return resp

    @post('/register/admin', expects=web.Expects('user', 'admin_register'),
          returns=web.Returns('user', 'private'), middlewares=['auth|roles=admin'])
    async def admin_register(self, payload):
        # send_mail = payload.pop('send_mail')
        payload['password'] = ''.join(random.choices(string.ascii_lowercase, k=32))
        user = await self.user_service.create(payload)
        # if send_mail:
        #     await mail.sender.send(payload['email'], 'Welcome!', 'Welcome to Bolinette!')
        return self.response.created('user.registered', user)

    @patch('/me', expects=web.Expects('user', 'register', patch=True), returns=web.Returns('user', 'private'),
           middlewares=['auth|fresh'])
    async def update_user(self, payload, current_user):
        user = await self.user_service.patch(current_user, payload)
        resp = self.response.ok('user.updated', user)
        self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
        return resp

    @post('/{username}/roles', expects=web.Expects('role'), returns=web.Returns('user', 'private'),
          middlewares=['auth|roles=admin'])
    async def add_user_role(self, match, payload):
        user = await self.user_service.get_by_username(match['username'])
        role = await self.role_service.get_by_name(payload['name'])
        await self.user_service.add_role(user, role)
        return self.response.created(f'user.roles.added:{user.username}:{role.name}', user)

    @delete('/{username}/roles/{role}', returns=web.Returns('user', 'private'), middlewares=['auth|roles=admin'])
    async def delete_user_role(self, match, current_user):
        user = await self.user_service.get_by_username(match['username'])
        role = await self.role_service.get_by_name(match['role'])
        await self.user_service.remove_role(current_user, user, role)
        return self.response.ok(f'user.roles.removed:{user.username}:{role.name}', user)

    @post('/picture', returns=web.Returns('user', 'private'), middlewares=['auth'])
    async def upload_profile_picture(self, current_user, payload):
        picture = payload['file']
        user = await self.user_service.save_profile_picture(current_user, picture)
        return self.response.ok(f'user.picture.uploaded', user)
