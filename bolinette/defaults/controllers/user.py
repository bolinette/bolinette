import random
import string
from datetime import datetime

from bolinette import blnt, types, core
from bolinette.decorators import controller, get, post, patch, delete
from bolinette.defaults.services import UserService, RoleService
from bolinette.exceptions import BadRequestError, EntityNotFoundError
from bolinette.utils import response, Cookie


@controller('user', '/user')
class UserController(blnt.Controller):
    @property
    def user_service(self) -> UserService:
        return self.context.service('user')
    
    @property
    def role_service(self) -> RoleService:
        return self.context.service('role')

    def default_routes(self):
        return [
            self.defaults.get_all('private', access=types.web.AccessToken.Required, roles=['admin']),
            self.defaults.get_one('private', key='username', access=types.web.AccessToken.Required, roles=['admin'])
        ]

    def _create_tokens(self, resp, user, *, set_access, set_refresh, fresh):
        now = datetime.utcnow()
        if set_access:
            access_token = self.context.jwt.create_access_token(now, user.username, fresh=fresh)
            resp.cookies.append(Cookie('access_token', access_token,
                                       expires=self.context.jwt.access_token_expires(now), path='/'))
        if set_refresh:
            refresh_token = self.context.jwt.create_refresh_token(now, user.username)
            resp.cookies.append(Cookie('refresh_token', refresh_token,
                                       expires=self.context.jwt.refresh_token_expires(now), path='/api/user/refresh'))

    @get('/me',
         access=types.web.AccessToken.Fresh,
         returns=('user', 'private'))
    async def me(self, current_user):
        return response.ok('OK', current_user)

    @get('/info',
         access=types.web.AccessToken.Required,
         returns=('user', 'private'))
    async def info(self, current_user):
        return response.ok('OK', current_user)

    @post('/login',
          returns=('user', 'private'),
          expects=('user', 'login'))
    async def login(self, payload):
        username = payload['username']
        password = payload['password']
        try:
            user = await self.user_service.get_by_username(username)
        except EntityNotFoundError:
            return response.unauthorized('user.login.wrong_credentials')
        if user is not None:
            if self.user_service.check_password(user, password):
                resp = response.ok('user.login.success', user)
                self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
                return resp
        return response.unauthorized('user.login.wrong_credentials')

    @post('/logout')
    async def logout(self):
        resp = response.ok('user.logout.success')
        resp.cookies.append(Cookie('access_token', None, delete=True, path='/'))
        resp.cookies.append(Cookie('refresh_token', None, delete=True, path='/api/user/refresh'))
        return resp

    @post('/token/refresh',
          access=types.web.AccessToken.Refresh)
    async def refresh(self, current_user):
        resp = response.ok('user.token.refreshed')
        self._create_tokens(resp, current_user, set_access=True, set_refresh=False, fresh=False)
        return resp

    @post('/register',
          returns=('user', 'private'),
          expects=('user', 'register'))
    async def register(self, payload):
        if core.init.get('ADMIN_REGISTER_ONLY', True):
            raise BadRequestError('global.register.admin_only')
        user = await self.user_service.create(payload)
        resp = response.created('user.registered', user)
        self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
        return resp

    @post('/register/admin',
          roles=['admin'],
          returns=('user', 'private'),
          expects=('user', 'admin_register'))
    async def admin_register(self, payload):
        # send_mail = payload.pop('send_mail')
        payload['password'] = ''.join(random.choices(string.ascii_lowercase, k=32))
        user = await self.user_service.create(payload)
        # if send_mail:
        #     await mail.sender.send(payload['email'], 'Welcome!', 'Welcome to Bolinette!')
        return response.created('user.registered', user)

    @patch('/me',
           access=types.web.AccessToken.Fresh,
           returns=('user', 'private'),
           expects=('user', 'register', 'patch'))
    async def update_user(self, payload, current_user):
        user = await self.user_service.patch(current_user, payload)
        resp = response.ok('user.updated', user)
        self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
        return resp

    @post('/{username}/roles',
          access=types.web.AccessToken.Required,
          roles=['admin'],
          expects='role',
          returns=('user', 'private'))
    async def add_user_role(self, match, payload):
        user = await self.user_service.get_by_username(match['username'])
        role = await self.role_service.get_by_name(payload['name'])
        await self.user_service.add_role(user, role)
        return response.created(f'user.roles.added:{user.username}:{role.name}', user)

    @delete('/{username}/roles/{role}',
            access=types.web.AccessToken.Required,
            roles=['admin'],
            returns=('user', 'private'))
    async def delete_user_role(self, match, current_user):
        user = await self.user_service.get_by_username(match['username'])
        role = await self.role_service.get_by_name(match['role'])
        await self.user_service.remove_role(current_user, user, role)
        return response.ok(f'user.roles.removed:{user.username}:{role.name}', user)

    @post('/picture',
          access=types.web.AccessToken.Required,
          returns=('user', 'private'))
    async def upload_profile_picture(self, current_user, payload):
        picture = payload['file']
        user = await self.user_service.save_profile_picture(current_user, picture)
        return response.ok(f'user.picture.uploaded', user)
