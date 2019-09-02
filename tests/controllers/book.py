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


def assert_equal_books(test, b1, b2, owner):
    test.assertEqual(b1['name'], b2['name'])
    test.assertEqual(b1['pages'], b2['pages'])
    test.assertEqual(b1['owner']['username'], owner['username'])


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
        assert_equal_books(self, rv['data'], book1, user1)

    def test_get_book2(self):
        user2 = create_mock(2, 'user', 'register')
        book3 = set_owner(create_mock(3, 'book'), 2)

        rv = self.client.get('/book/3')
        self.assertEqual(rv['code'], 200)
        assert_equal_books(self, rv['data'], book3, user2)

    def test_get_book_not_found(self):
        rv = self.client.get('/book/4')
        self.assertEqual(rv['code'], 404)

    def test_create_book(self):
        user1 = create_mock(1, 'user', 'register')
        book4 = set_owner(create_mock(4, 'book'), 1)

        rv = self.client.post('/book', book4)
        self.assertEqual(rv['code'], 201)
        assert_equal_books(self, rv['data'], book4, user1)

    def test_create_book_bad_request(self):
        rv = self.client.post('/book', {})
        self.assertEqual(rv['code'], 400)
        self.assertSetEqual(set(rv['messages']), {'param.required:name',
                                                  'param.required:pages',
                                                  'param.required:owner_id'})

    def test_create_book_user_not_found(self):
        book4 = set_owner(create_mock(4, 'book'), 3)

        rv = self.client.post('/book', book4)
        self.assertEqual(rv['code'], 404)
        self.assertSetEqual(set(rv['messages']), {'user.not_found:id:3'})

    def test_update_book(self):
        user2 = create_mock(2, 'user', 'register')
        book5 = set_owner(create_mock(1, 'book'), 2)

        rv = self.client.put('/book/1', book5)
        self.assertEqual(rv['code'], 200)
        assert_equal_books(self, rv['data'], book5, user2)

    def test_update_book_not_found(self):
        rv = self.client.put('/book/4', {'name': 'new book name'})
        self.assertEqual(rv['code'], 404)

    def test_partial_update_book(self):
        rv = self.client.put('/book/1', {'name': 'new book name'})
        self.assertEqual(rv['code'], 200)
        self.assertEqual(rv['data']['name'], 'new book name')

    def test_partial_update_book_bad_request(self):
        rv = self.client.put('/book/1', {'name': ''})
        self.assertEqual(rv['code'], 400)
        self.assertSetEqual(set(rv['messages']), {'param.required:name'})

    def test_update_book_user_not_found(self):
        rv = self.client.put('/book/1', {'owner_id': 3})
        self.assertEqual(rv['code'], 404)
        self.assertSetEqual(set(rv['messages']), {'user.not_found:id:3'})

    def test_delete_book(self):
        rv = self.client.delete('/book/1')
        self.assertEqual(rv['code'], 200)

        rv = self.client.get('/book/1')
        self.assertEqual(rv['code'], 404)

    def test_delete_book_not_found(self):
        rv = self.client.delete('/book/4')
        self.assertEqual(rv['code'], 404)
