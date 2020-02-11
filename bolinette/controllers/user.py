from flask import after_this_request
from flask_jwt_extended import (
    create_access_token, create_refresh_token, set_access_cookies, set_refresh_cookies,
    get_jwt_identity, unset_jwt_cookies, current_user
)
from bolinette import Namespace, response, AccessToken
from bolinette.exceptions import EntityNotFoundError
from bolinette.services import user_service, role_service

ns = Namespace(user_service, '/user')


@ns.route('/me',
          methods=['GET'],
          access=AccessToken.Fresh,
          returns=ns.route.returns('user', 'private'))
def me():
    return response.ok('OK', current_user)


@ns.route('/me',
          methods=['PATCH'],
          access=AccessToken.Fresh,
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'register', patch=True))
def update_user(payload):
    user = user_service.get_by_username(get_jwt_identity())
    user = user_service.patch(user, payload)
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
          access=AccessToken.Required,
          returns=ns.route.returns('user', 'private'))
def info():
    return response.ok('OK', current_user)


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
          returns=ns.route.returns('user', 'private'),
          expects=ns.route.expects('user', 'register'))
def register(payload):
    user = user_service.create(payload)
    return response.created('User successfully registered', user)


@ns.route('/token/refresh',
          methods=['POST'],
          access=AccessToken.Refresh)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity, fresh=False)

    @after_this_request
    def reset_cookies(resp):
        set_access_cookies(resp, access_token)
        return resp

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
    if role.name == 'root':
        return response.forbidden('role.root.forbidden')
    if role in user.roles:
        return response.bad_request(f'user.roles.exists:{user.username}:{role.name}')
    user.roles.append(role)
    return response.created(f'user.roles.added:{user.username}:{role.name}', user)


@ns.route('/<username>/roles/<role>',
          methods=['DELETE'],
          roles=['admin'],
          returns=ns.route.returns('user', 'private'))
def delete_user_role(username, role):
    user = user_service.get_by_username(username)
    role = role_service.get_by_name(role)
    if role.name == 'root':
        return response.forbidden('role.root.forbidden')
    if (current_user.username == user.username
            and role.name == 'admin'
            and not current_user.has_role('root')):
        return response.forbidden('role.admin.no_self_demotion')
    if role in user.roles:
        user.roles.remove(role)
        return response.ok(f'user.roles.deleted:{user.username}:{role.name}', user)
    return response.bad_request(f'user.roles.not_found:{user.username}:{role.name}')


ns.register()
