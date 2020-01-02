from flask import after_this_request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies,
    get_jwt_identity, jwt_refresh_token_required, unset_jwt_cookies,
    current_user, jwt_required, fresh_jwt_required)

from bolinette import Namespace, response, transactional
from bolinette.exceptions import EntityNotFoundError
from bolinette.services import user_service

ns = Namespace(user_service, '/user')


@ns.route('/me',
          methods=['GET'],
          returns={'model': 'user', 'key': 'private'})
@fresh_jwt_required
def me():
    return response.ok('OK', current_user)


@ns.route('/me',
          methods=['PUT'],
          returns={'model': 'user', 'key': 'private'},
          expects={'model': 'user', 'key': 'register', 'patch': True})
@fresh_jwt_required
def update_user(payload):
    user = user_service.get_by_username(get_jwt_identity())
    user = user_service.update(user, payload)
    access_token = create_access_token(identity=user.username, fresh=True)
    refresh_token = create_refresh_token(identity=user.username)

    @after_this_request
    def set_login_cookies(resp):
        set_access_cookies(resp, access_token)
        set_refresh_cookies(resp, refresh_token)
        return resp

    return response.ok('user.updated', user)


@ns.route('/info',
          methods=['GET'],
          returns={'model': 'user', 'key': 'public'})
@jwt_required
def info():
    return response.ok('OK', current_user)


@ns.route('/login',
          methods=['POST'],
          returns={'model': 'user', 'key': 'private'},
          expects={'model': 'user', 'key': 'login'})
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

            @after_this_request
            def set_login_cookies(resp):
                set_access_cookies(resp, access_token)
                set_refresh_cookies(resp, refresh_token)
                return resp

            return response.ok('user.login.success', user)
    return response.unauthorized('user.login.wrong_credentials')


@ns.route('/logout',
          methods=['POST'])
def logout():
    @after_this_request
    def unset_cookies(resp):
        unset_jwt_cookies(resp)
        return resp

    return response.ok('user.logout.success')


@ns.route('/register',
          methods=['POST'],
          returns={'model': 'user', 'key': 'private'},
          expects={'model': 'user', 'key': 'register'})
def register(payload):
    user = user_service.create(payload)
    return response.created('User successfully registered', user)


@ns.route('/token/refresh',
          methods=['POST'])
@jwt_refresh_token_required
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, fresh=False)

    @after_this_request
    def reset_cookies(resp):
        set_access_cookies(resp, access_token)
        return resp

    return response.ok('user.token.refreshed')


ns.register()
