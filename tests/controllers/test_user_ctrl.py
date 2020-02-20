import pytest

from bolinette import bcrypt
from bolinette.models import User, Role
from bolinette.testing import client, bolitest, create_mock, insert


def salt_password(mock):
    mock['password'] = bcrypt.generate_password_hash(mock['password'])
    return mock


def set_up():
    insert(User, salt_password(create_mock(1, 'user', 'register')))


def admin_set_up():
    admin = insert(Role, {'name': 'admin'})
    user1 = insert(User, salt_password(create_mock(1, 'user', 'register')))
    user1.roles.append(admin)
    insert(User, salt_password(create_mock(2, 'user', 'register')))
    insert(Role, create_mock(1, 'role'))


def root_set_up():
    root = insert(Role, {'name': 'root'})
    admin = insert(Role, {'name': 'admin'})
    user1 = insert(User, salt_password(create_mock(1, 'user', 'register')))
    user1.roles.append(root)
    user1.roles.append(admin)


@bolitest(before=set_up)
def test_login_failed(client):
    user1 = create_mock(1, 'user', 'register')

    rv = client.post('/user/login', {'username': user1['username'],
                                     'password': user1['password'][:-1]})
    assert rv['code'] == 401
    assert 'user.login.wrong_credentials' in rv['messages']

    rv = client.post('/user/login', {'username': user1['username'] + "2",
                                     'password': user1['password']})
    assert rv['code'] == 401
    assert 'user.login.wrong_credentials' in rv['messages']


@bolitest(before=set_up)
def test_login(client):
    user1 = create_mock(1, 'user', 'register')

    rv = client.post('/user/login', user1)
    assert rv['code'] == 200


@bolitest(before=set_up)
def test_access_user_info_failed(client):
    rv = client.get('/user/me')
    assert rv['code'] == 401


@bolitest(before=set_up)
def test_access_user_info(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.get('/user/me')
    assert rv['code'] == 200
    assert rv['data'].get('username') == user1['username']
    assert rv['data'].get('email') == user1['email']
    assert rv['data'].get('password') is None


@bolitest(before=set_up)
def test_logout(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.get('/user/me')
    assert rv['code'] == 200

    rv = client.post('/user/logout')
    assert rv['code'] == 200

    rv = client.get('/user/me')
    assert rv['code'] == 401


@bolitest(before=set_up)
def test_register(client):
    user2 = create_mock(2, 'user', 'register')

    rv = client.post('/user/register', user2)
    assert rv['code'] == 201

    rv = client.post('/user/login', user2)
    assert rv['code'] == 200


@bolitest(before=set_up)
def test_register_bad_request(client):
    rv = client.post('/user/register', {})
    assert rv['code'] == 400
    assert 'param.required:username' in rv['messages']
    assert 'param.required:password' in rv['messages']
    assert 'param.required:email' in rv['messages']


@bolitest(before=set_up)
def test_register_conflict(client):
    user1 = create_mock(1, 'user', 'register')

    rv = client.post('/user/register', user1)
    assert rv['code'] == 409
    assert f'param.conflict:username:{user1["username"]}' in rv['messages']
    assert f'param.conflict:email:{user1["email"]}' in rv['messages']


@bolitest(before=set_up)
def test_change_username(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.patch('/user/me', {'username': 'new_username'})
    assert rv['code'] == 200
    assert rv['data']['username'] == 'new_username'
    assert rv['data']['email'] == user1['email']


@bolitest(before=set_up)
def test_change_password(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.patch('/user/me', {'password': 'new_password'})

    client.post('/user/logout')
    rv = client.post('/user/login', {'username': user1['username'], 'password': 'new_password'})

    rv = client.get('/user/me')
    assert rv['code'] == 200


@bolitest(before=admin_set_up)
def test_get_users(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.get('/user')
    assert rv['code'] == 200
    assert len(rv['data']) == 2


@bolitest(before=admin_set_up)
def test_get_users_forbidden(client):
    user1 = create_mock(2, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.get('/user')
    assert rv['code'] == 403
    assert 'user.forbidden:admin' in rv['messages']


@bolitest(before=admin_set_up)
def test_add_self_role(client):
    user1 = create_mock(1, 'user', 'register')
    role1 = create_mock(1, 'role')

    client.post('/user/login', user1)

    rv = client.post(f'/user/{user1["username"]}/roles', role1)
    assert rv['code'] == 201
    assert f'user.roles.added:{user1["username"]}:{role1["name"]}' in rv['messages']


@bolitest(before=admin_set_up)
def test_add_role_not_admin(client):
    user2 = create_mock(2, 'user', 'register')
    role1 = create_mock(1, 'role')

    client.post('/user/login', user2)

    rv = client.post(f'/user/{user2["username"]}/roles', role1)
    assert rv['code'] == 403
    assert f'user.forbidden:admin' in rv['messages']


@bolitest(before=admin_set_up)
def test_remove_role(client):
    user1 = create_mock(1, 'user', 'register')
    role1 = create_mock(1, 'role')

    client.post('/user/login', user1)
    client.post(f'/user/{user1["username"]}/roles', role1)

    rv = client.delete(f'/user/{user1["username"]}/roles/{role1["name"]}')
    assert rv['code'] == 200
    assert f'user.roles.removed:{user1["username"]}:{role1["name"]}' in rv['messages']


@bolitest(before=admin_set_up)
def test_remove_role_not_found(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.delete(f'/user/{user1["username"]}/roles/unknow_role')
    assert rv['code'] == 404
    assert f'role.not_found:name:unknow_role' in rv['messages']


@bolitest(before=admin_set_up)
def test_remove_role_not_in_user_roles(client):
    user1 = create_mock(1, 'user', 'register')
    role1 = create_mock(1, 'role')

    client.post('/user/login', user1)

    rv = client.delete(f'/user/{user1["username"]}/roles/{role1["name"]}')
    assert rv['code'] == 400
    assert f'user.roles.not_found:{user1["username"]}:{role1["name"]}' in rv['messages']


@bolitest(before=admin_set_up)
def test_no_self_demotion(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.delete(f'/user/{user1["username"]}/roles/admin')
    assert rv['code'] == 403
    assert f'role.admin.no_self_demotion' in rv['messages']


@bolitest(before=root_set_up)
def test_root_self_demotion(client):
    user1 = create_mock(1, 'user', 'register')

    client.post('/user/login', user1)

    rv = client.delete(f'/user/{user1["username"]}/roles/admin')
    assert rv['code'] == 200
    assert f'user.roles.removed:{user1["username"]}:admin' in rv['messages']
