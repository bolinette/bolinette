import random
import string

from flask import after_this_request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies,
    get_jwt_identity, unset_jwt_cookies
)
from bolinette import env, response, mail
from bolinette.exceptions import EntityNotFoundError, BadRequestError
from bolinette.routing import Namespace, current_user, AccessToken
from bolinette.services import user_service, role_service

ns = Namespace(user_service, '/user')


def _set_login_cookies(access_token, refresh_token):
    def inner(resp):
        set_access_cookies(resp, access_token)
        set_refresh_cookies(resp, refresh_token)
        return resp
    return inner


def _reset_cookies(access_token):
    def inner(resp):
        set_access_cookies(resp, access_token)
        return resp
    return inner


def _unset_cookies(resp):
    unset_jwt_cookies(resp)
    return resp


@ns.route('/me',
          methods=['GET'],
          access=AccessToken.Fresh,
          returns=ns.route.returns('user', 'private'))
def me():
    return response.ok('OK', current_user())


@ns.route('/me',
          methods=['PATCH'],
          access=AccessToken.Fresh,
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'register', patch=True))
def update_user(payload):
    user = user_service.patch(current_user(), payload)
    access_token = create_access_token(identity=user.username, fresh=True)
    refresh_token = create_refresh_token(identity=user.username)
    after_this_request(_set_login_cookies(access_token, refresh_token))
    return response.ok('user.updated', user)


@ns.route('/info',
          methods=['GET'],
          access=AccessToken.Required,
          returns=ns.route.returns('user', 'private'))
def info():
    return response.ok('OK', current_user())


@ns.route('/login',
          methods=['POST'],
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'login'))
def login(payload):
    """
    Logs the user in with the provided credentials
    """
    username = payload['username']
    password = payload['password']
    try:
        user = user_service.get_by_username(username)
    except EntityNotFoundError:
        return response.unauthorized('user.login.wrong_credentials')
    if user is not None:
        if user_service.check_password(user, password):
            access_token = create_access_token(identity=user.username, fresh=True)
            refresh_token = create_refresh_token(identity=user.username)
            after_this_request(_set_login_cookies(access_token, refresh_token))
            return response.ok('user.login.success', user)
    return response.unauthorized('user.login.wrong_credentials')


@ns.route('/logout',
          methods=['POST'])
def logout():
    after_this_request(_unset_cookies)
    return response.ok('user.logout.success')


@ns.route('/register',
          methods=['POST'],
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'register'))
def register(payload):
    if env.init.get('ADMIN_REGISTER_ONLY', True):
        raise BadRequestError('global.register.admin_only')
    if current_user() is not None:
        raise BadRequestError('global.register.logged_in')
    user = user_service.create(payload)
    access_token = create_access_token(identity=user.username, fresh=True)
    refresh_token = create_refresh_token(identity=user.username)
    after_this_request(_set_login_cookies(access_token, refresh_token))
    return response.created('user.registered', user)


@ns.route('/register/admin',
          methods=['POST'],
          roles=['adminn'],
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'admin_register'))
def admin_register(payload):
    send_mail = payload.pop('send_mail')
    payload['password'] = ''.join(random.choices(string.ascii_lowercase, k=32))
    user = user_service.create(payload)
    if send_mail:
        mail.sender.send(payload['email'], 'Welcome!', 'Welcome to Bolinette!')
    return response.created('user.registered', user)


@ns.route('/token/refresh',
          methods=['POST'],
          access=AccessToken.Refresh)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, fresh=False)
    after_this_request(_reset_cookies(access_token))
    return response.ok('user.token.refreshed')


ns.defaults.get_all('private', roles=['admin'])

ns.defaults.get_first_by('username', returns='private', roles=['admin'])


@ns.route('/<username>/roles',
          methods=['POST'],
          roles=['admin'],
          expects=ns.route.expects('role'),
          returns=ns.route.returns('user', 'private'))
def add_user_role(username, payload):
    user = user_service.get_by_username(username)
    role = role_service.get_by_name(payload['name'])
    user_service.add_role(user, role)
    return response.created(f'user.roles.added:{user.username}:{role.name}', user)


@ns.route('/<username>/roles/<role>',
          methods=['DELETE'],
          roles=['admin'],
          returns=ns.route.returns('user', 'private'))
def delete_user_role(username, role):
    user = user_service.get_by_username(username)
    role = role_service.get_by_name(role)
    user_service.remove_role(current_user(), user, role)
    return response.ok(f'user.roles.removed:{user.username}:{role.name}', user)


ns.register()
