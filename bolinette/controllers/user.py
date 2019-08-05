from flask import after_this_request
from flask_jwt_extended import (create_access_token, create_refresh_token, set_access_cookies,
                                set_refresh_cookies, get_jwt_identity, jwt_refresh_token_required,
                                jwt_required)

from bolinette import Namespace, response, transactional
from bolinette.exceptions import EntityNotFoundError
from bolinette.marshalling import expects, returns
from bolinette.services import user_service

ns = Namespace('user', '/user')


@ns.route('/me', methods=['GET'])
@jwt_required
@returns('user', 'private')
@transactional
def me():
    return response.ok('OK', user_service.get_by_username(get_jwt_identity()))


@ns.route('/login', methods=['POST'])
@transactional
@expects('user', 'login')
def login(payload):
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
            return response.ok('user.login.success')
    return response.unauthorized('user.login.wrong_credentials')


@ns.route('/register', methods=['POST'])
@returns('user', 'private')
@transactional
@expects('user', 'register')
def register(payload):
    user = user_service.create(**payload)
    return response.created('User successfully registered', user)


@ns.route('/token/refresh', methods=['POST'])
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
