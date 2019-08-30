import unittest

from bolinette import Bolinette, bcrypt
from bolinette.models import User

from bolinette.testing import TestClient, create_mock, insert


def salt_password(mock):
    mock['password'] = bcrypt.generate_password_hash(mock['password'])
    return mock


class TestUserController(unittest.TestCase):
    def __init__(self, method):
        super().__init__(method)
        self.client = TestClient(Bolinette(__name__))

    def setUp(self):
        self.client.set_up()
        insert(User, salt_password(create_mock(1, 'user', 'register')))

    def tearDown(self):
        self.client.tear_down()

    def test_login_failed(self):
        user1 = create_mock(1, 'user', 'register')

        rv = self.client.post('/user/login', {'username': user1['username'],
                                              'password': user1['password'][:-1]})
        self.assertEqual(rv['code'], 401)
        self.assertSetEqual(set(rv['messages']), {'user.login.wrong_credentials'})

        rv = self.client.post('/user/login', {'username': user1['username'] + "2",
                                              'password': user1['password']})
        self.assertEqual(rv['code'], 401)
        self.assertSetEqual(set(rv['messages']), {'user.login.wrong_credentials'})

    def test_login(self):
        user1 = create_mock(1, 'user', 'register')

        rv = self.client.post('/user/login', user1)
        self.assertEqual(rv['code'], 200)

    def test_access_user_info_failed(self):
        rv = self.client.get('/user/me')
        self.assertEqual(rv['code'], 401)

    def test_access_user_info(self):
        user1 = create_mock(1, 'user', 'register')

        self.client.post('/user/login', user1)

        rv = self.client.get('/user/me')
        self.assertEqual(rv['code'], 200)
        self.assertEqual(rv['data'].get('username'), user1['username'])
        self.assertEqual(rv['data'].get('email'), user1['email'])
        self.assertEqual(rv['data'].get('password'), None)

    def test_logout(self):
        user1 = create_mock(1, 'user', 'register')

        self.client.post('/user/login', user1)

        rv = self.client.get('/user/me')
        self.assertEqual(rv['code'], 200)

        rv = self.client.post('/user/logout')
        self.assertEqual(rv['code'], 200)

        rv = self.client.get('/user/me')
        self.assertEqual(rv['code'], 401)

    def test_register(self):
        user2 = create_mock(2, 'user', 'register')

        rv = self.client.post('/user/register', user2)
        self.assertEqual(rv['code'], 201)

        rv = self.client.post('/user/login', user2)
        self.assertEqual(rv['code'], 200)

    def test_register_bad_request(self):
        rv = self.client.post('/user/register', {})
        self.assertEqual(rv['code'], 400)
        self.assertSetEqual(set(rv['messages']), {'param.required:username',
                                                  'param.required:password',
                                                  'param.required:email'})

    def test_register_conflict(self):
        user1 = create_mock(1, 'user', 'register')

        rv = self.client.post('/user/register', user1)
        self.assertEqual(rv['code'], 409)
        self.assertSetEqual(set(rv['messages']),
                            {f'param.conflict:username:{user1["username"]}',
                             f'param.conflict:email:{user1["email"]}'})
