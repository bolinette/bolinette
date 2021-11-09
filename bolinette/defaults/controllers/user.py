import random
import string
from datetime import datetime

from bolinette import abc, blnt, web
from bolinette.decorators import controller, get, post, patch, delete
from bolinette.defaults.services import UserService, RoleService
from bolinette.exceptions import ForbiddenError


@controller('user', '/user')
class UserController(web.Controller):
    def __init__(self, context: abc.Context, user_service: UserService, role_service: 'RoleService'):
        super().__init__(context)
        self.user_service = user_service
        self.role_service = role_service

    def default_routes(self):
        return [
            self.defaults.get_all('private', middlewares=['auth|roles=admin']),
            self.defaults.get_one('private', prefix='/u', key='username', middlewares=['auth|roles=admin'])
        ]

    def _create_tokens(self, resp, user, *, set_access, set_refresh, fresh):
        cookies = self.context.env['credentials'] == 'cookies'
        now = datetime.utcnow()
        access_token = None
        refresh_token = None
        if set_access:
            access_token = self.context.jwt.create_access_token(now, user.username, fresh=fresh)
            if cookies:
                resp.cookies.append(web.Cookie('access_token', access_token, http_only=True, path='/'))
        if set_refresh:
            refresh_token = self.context.jwt.create_refresh_token(now, user.username)
            if cookies:
                resp.cookies.append(web.Cookie('refresh_token', refresh_token,
                                               http_only=True, path='/api/user/token/refresh'))
        return access_token, refresh_token

    @get('/info', returns=web.Returns('user', 'private'), middlewares=['auth'])
    async def info(self, current_user):
        """
        Gets current user's details
        """
        return current_user

    @post('/login', expects=web.Expects('user', 'login'), returns=web.Returns('user', 'private'))
    async def login(self, payload):
        """
        Logs the user in, setting the JWT inside the cookies
        """
        username = payload['username']
        password = payload['password']
        user = await self.user_service.get_by_username(username, safe=True)
        if user is not None:
            if self.user_service.check_password(user, password):
                resp = self.response.ok(messages='user.login.success', data=user)
                a_token, r_token = self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
                if a_token:
                    resp.content['access_token'] = a_token
                if r_token:
                    resp.content['refresh_token'] = r_token
                return resp
        return self.response.unauthorized(messages='user.login.wrong_credentials')

    @post('/logout')
    async def logout(self):
        """
        Deletes authentication cookies, effectively logging the user off
        """
        resp = self.response.ok(messages='user.logout.success')
        resp.cookies.append(web.Cookie('access_token', None, delete=True, path='/'))
        resp.cookies.append(web.Cookie('refresh_token', None, delete=True, path='/api/user/token/refresh'))
        return resp

    @post('/token/refresh', middlewares=['auth|refresh'])
    async def refresh(self, current_user):
        """
        Creates a new fresh JWT
        """
        resp = self.response.ok(messages='user.token.refreshed')
        a_token, _ = self._create_tokens(resp, current_user, set_access=True, set_refresh=False, fresh=False)
        if a_token:
            resp.content['access_token'] = a_token
        return resp

    @post('/register', expects=web.Expects('user', 'register'), returns=web.Returns('user', 'private'))
    async def register(self, payload):
        """
        Creates a new user from given information

        If the init parameter ADMIN_REGISTER_ONLY is true, only admin users can create new accounts and
        the route will send back a 403 FORBIDDEN.

        -response 201 returns: The created user
        -response 403: If the route is disabled
        """
        if blnt.init.get('ADMIN_REGISTER_ONLY', True):
            raise ForbiddenError('global.register.admin_only')
        user = await self.user_service.create(payload)
        resp = self.response.created(messages='user.registered', data=user)
        a_token, r_token = self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
        if a_token:
            resp.content['access_token'] = a_token
        if r_token:
            resp.content['refresh_token'] = r_token
        return resp

    @post('/register/admin', expects=web.Expects('user', 'admin_register'),
          returns=web.Returns('user', 'private'), middlewares=['auth|roles=admin'])
    async def admin_register(self, payload):
        """
        Creates a new user from given information and a random password

        Admin only route.
        """
        payload['password'] = ''.join(random.choices(string.ascii_lowercase, k=32))
        user = await self.user_service.create(payload)
        return self.response.created(messages='user.registered', data=user)

    @patch('/me', expects=web.Expects('user', 'register', patch=True), returns=web.Returns('user', 'private'),
           middlewares=['auth|fresh'])
    async def update_user(self, payload, current_user):
        """
        Updates current user information from payload

        Requires a fresh JWT.
        """
        user = await self.user_service.patch(current_user, payload)
        resp = self.response.ok(messages='user.updated', data=user)
        a_token, r_token = self._create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
        if a_token:
            resp.content['access_token'] = a_token
        if r_token:
            resp.content['refresh_token'] = r_token
        return resp

    @post('/{username}/roles', expects=web.Expects('role'), returns=web.Returns('user', 'private'),
          middlewares=['auth|roles=admin'])
    async def add_user_role(self, match, payload):
        """
        Adds a role to the user identified by username param

        Admin only route.
        """
        user = await self.user_service.get_by_username(match['username'])
        role = await self.role_service.get_by_name(payload['name'])
        await self.user_service.add_role(user, role)
        return self.response.created(messages=f'user.roles.added:{user.username}:{role.name}', data=user)

    @delete('/{username}/roles/{role}', returns=web.Returns('user', 'private'), middlewares=['auth|roles=admin'])
    async def delete_user_role(self, match, current_user):
        """
        Removes a role from the user identified by username parameter

        Admin only route.
        """
        user = await self.user_service.get_by_username(match['username'])
        role = await self.role_service.get_by_name(match['role'])
        await self.user_service.remove_role(current_user, user, role)
        return self.response.ok(messages=f'user.roles.removed:{user.username}:{role.name}', data=user)

    @post('/picture', returns=web.Returns('user', 'private'), middlewares=['auth'])
    async def upload_profile_picture(self, current_user, payload):
        """
        Uploads a profile picture for the current user
        """
        picture = payload['file']
        user = await self.user_service.save_profile_picture(current_user, picture)
        return self.response.ok(messages=f'user.picture.uploaded', data=user)
