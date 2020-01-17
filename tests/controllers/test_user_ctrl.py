import pytest

from bolinette import bcrypt
from bolinette.models import User
from bolinette.testing import client, bolitest, create_mock, insert


def salt_password(mock):
    mock['password'] = bcrypt.generate_password_hash(mock['password'])
    return mock


def set_up():
    insert(User, salt_password(create_mock(1, 'user', 'register')))


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
    assert rv['data'].get('password') == None


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
