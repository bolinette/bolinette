import string
from datetime import datetime
from random import random

from bolinette import response, jwt, Cookie, mail, env
from bolinette.exceptions import EntityNotFoundError, BadRequestError
from bolinette.routing import Namespace, Method, AccessType
from bolinette.services import user_service, role_service

ns = Namespace('/user', user_service)


def _create_tokens(resp, user, *, set_access, set_refresh, fresh):
    now = datetime.utcnow()
    if set_access:
        access_token = jwt.create_access_token(now, user.username, fresh=fresh)
        resp.cookies.append(Cookie('access_token', access_token,
                                   expires=jwt.access_token_expires(now), path='/api'))
    if set_refresh:
        refresh_token = jwt.create_refresh_token(now, user.username)
        resp.cookies.append(Cookie('refresh_token', refresh_token,
                                   expires=jwt.refresh_token_expires(now), path='/api/user/refresh'))


@ns.route('/me',
          method=Method.GET,
          access=AccessType.Fresh,
          returns=ns.route.returns('user', 'private'))
async def me(current_user, **_):
    return response.ok('OK', current_user)


@ns.route('/info',
          method=Method.GET,
          access=AccessType.Required,
          returns=ns.route.returns('user', 'private'))
async def info(current_user, **_):
    return response.ok('OK', current_user)


@ns.route('/login',
          method=Method.POST,
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'login'))
async def login(payload, **_):
    username = payload['username']
    password = payload['password']
    try:
        user = await user_service.get_by_username(username)
    except EntityNotFoundError:
        return response.unauthorized('user.login.wrong_credentials')
    if user is not None:
        if await user_service.check_password(user, password):
            resp = response.ok('user.login.success', user)
            _create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
            return resp
    return response.unauthorized('user.login.wrong_credentials')


@ns.route('/logout',
          method=Method.POST)
async def logout(**_):
    resp = response.ok('user.logout.success')
    resp.cookies.append(Cookie('access_token', None, delete=True, path='/api'))
    resp.cookies.append(Cookie('refresh_token', None, delete=True, path='/api/user/refresh'))
    return resp


@ns.route('/token/refresh',
          method=Method.POST,
          access=AccessType.Refresh)
async def refresh(current_user, **_):
    resp = response.ok('user.token.refreshed')
    _create_tokens(resp, current_user, set_access=True, set_refresh=False, fresh=False)
    return resp


@ns.route('/register',
          method=Method.POST,
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'register'))
async def register(payload, **_):
    if env.init.get('ADMIN_REGISTER_ONLY', True):
        raise BadRequestError('global.register.admin_only')
    user = await user_service.create(payload)
    resp = response.created('user.registered', user)
    _create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
    return resp


@ns.route('/register/admin',
          method=Method.POST,
          roles=['admin'],
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'admin_register'))
async def admin_register(payload, **_):
    send_mail = payload.pop('send_mail')
    payload['password'] = ''.join(random.choices(string.ascii_lowercase, k=32))
    user = await user_service.create(payload)
    if send_mail:
        await mail.sender.send(payload['email'], 'Welcome!', 'Welcome to Bolinette!')
    return response.created('user.registered', user)


@ns.route('/me',
          method=Method.PATCH,
          access=AccessType.Fresh,
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'register', patch=True))
async def update_user(payload, current_user, **_):
    user = await user_service.patch(current_user, payload)
    resp = response.ok('user.updated', user)
    _create_tokens(resp, user, set_access=True, set_refresh=True, fresh=True)
    return resp


ns.defaults.get_all('private', access=AccessType.Required, roles=['admin'])

ns.defaults.get_first_by('username', returns='private', access=AccessType.Required, roles=['admin'])


@ns.route('/{username}/roles',
          method=Method.POST,
          access=AccessType.Required,
          roles=['admin'],
          expects=ns.route.expects('role'),
          returns=ns.route.returns('user', 'private'))
async def add_user_role(match, payload, **_):
    user = await user_service.get_by_username(match['username'])
    role = await role_service.get_by_name(payload['name'])
    await user_service.add_role(user, role)
    return response.created(f'user.roles.added:{user.username}:{role.name}', user)


@ns.route('/{username}/roles/{role}',
          method=Method.DELETE,
          access=AccessType.Required,
          roles=['admin'],
          returns=ns.route.returns('user', 'private'))
async def delete_user_role(match, current_user, **_):
    user = await user_service.get_by_username(match['username'])
    role = await role_service.get_by_name(match['role'])
    await user_service.remove_role(current_user, user, role)
    return response.ok(f'user.roles.removed:{user.username}:{role.name}', user)


@ns.route('/picture',
          method=Method.POST,
          access=AccessType.Required,
          returns=ns.route.returns('user', 'private'))
async def upload_profile_picture(current_user, payload, **_):
    picture = payload['file']
    user = await user_service.save_profile_picture(current_user, picture)
    return response.ok(f'user.picture.uploaded', user)
