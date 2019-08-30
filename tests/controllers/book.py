import unittest

from bolinette import Bolinette, bcrypt
from bolinette.models import User
from bolinette.testing import TestClient, insert, create_mock
from example.models import Book


def set_owner(mock, owner_id):
    mock['owner_id'] = owner_id
    return mock


def salt_password(mock):
    mock['password'] = bcrypt.generate_password_hash(mock['password'])
    return mock


class TestBookController(unittest.TestCase):
    def __init__(self, method):
        super().__init__(method)
        self.client = TestClient(Bolinette(__name__))

    def setUp(self):
        self.client.set_up()
        insert(User, salt_password(create_mock(1, 'user', 'register')))
        insert(User, salt_password(create_mock(2, 'user', 'register')))
        insert(Book, set_owner(create_mock(1, 'book'), 1))
        insert(Book, set_owner(create_mock(2, 'book'), 1))
        insert(Book, set_owner(create_mock(3, 'book'), 2))

    def tearDown(self):
        self.client.tear_down()

    def test_get_books(self):
        rv = self.client.get('/book')
        self.assertEqual(rv['code'], 200)
        self.assertTrue(len(rv['data']) == 3)

    def test_get_book(self):
        user1 = create_mock(1, 'user', 'register')
        book1 = set_owner(create_mock(1, 'book'), 1)

        rv = self.client.get('/book/1')
        self.assertEqual(rv['code'], 200)
        self.assertEqual(rv['data']['name'], book1['name'])
        self.assertEqual(rv['data']['owner']['username'], user1['username'])

    def test_get_book2(self):
        user2 = create_mock(2, 'user', 'register')
        book3 = set_owner(create_mock(3, 'book'), 2)

        rv = self.client.get('/book/3')
        self.assertEqual(rv['code'], 200)
        self.assertEqual(rv['data']['name'], book3['name'])
        self.assertEqual(rv['data']['owner']['username'], user2['username'])

    def test_get_book_failed(self):
        rv = self.client.get('/book/4')
        self.assertEqual(rv['code'], 404)
