import pytest

from bolinette import bcrypt
from bolinette.models import User
from bolinette.testing import client, bolitest, create_mock, insert

from example.models import Book


def salt_password(mock):
    mock['password'] = bcrypt.generate_password_hash(mock['password'])
    return mock


def set_owner(mock, owner_id):
    mock['owner_id'] = owner_id
    return mock


def set_up():
    insert(User, salt_password(create_mock(1, 'user', 'register')))
    insert(User, salt_password(create_mock(2, 'user', 'register')))
    insert(Book, set_owner(create_mock(1, 'book'), 1))
    insert(Book, set_owner(create_mock(2, 'book'), 1))
    insert(Book, set_owner(create_mock(3, 'book'), 2))


def assert_equal_books(b1, b2, owner):
    assert b1['name'] == b2['name']
    assert b1['pages'] == b2['pages']
    assert b1['owner']['username'] == owner['username']


@bolitest(before=set_up)
def test_get_books(client):
    rv = client.get('/book')
    assert rv['code'] == 200
    assert len(rv['data']) == 3


@bolitest(before=set_up)
def test_get_book(client):
    user1 = create_mock(1, 'user', 'register')
    book1 = set_owner(create_mock(1, 'book'), 1)

    rv = client.get('/book/1')
    assert rv['code'] == 200
    assert_equal_books(rv['data'], book1, user1)


@bolitest(before=set_up)
def test_get_book2(client):
    user2 = create_mock(2, 'user', 'register')
    book3 = set_owner(create_mock(3, 'book'), 2)

    rv = client.get('/book/3')
    assert rv['code'] == 200
    assert_equal_books(rv['data'], book3, user2)


@bolitest(before=set_up)
def test_get_book_not_found(client):
    rv = client.get('/book/4')
    assert rv['code'] == 404


@bolitest(before=set_up)
def test_create_book(client):
    user1 = create_mock(1, 'user', 'register')
    book4 = set_owner(create_mock(4, 'book'), 1)

    rv = client.post('/book', book4)
    assert rv['code'] == 201
    assert_equal_books(rv['data'], book4, user1)


@bolitest(before=set_up)
def test_create_book_bad_request(client):
    rv = client.post('/book', {})
    assert rv['code'] == 400
    assert 'param.required:name' in rv['messages']
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:owner_id' in rv['messages']


@bolitest(before=set_up)
def test_create_book_user_not_found(client):
    book4 = set_owner(create_mock(4, 'book'), 3)

    rv = client.post('/book', book4)
    assert rv['code'] == 404
    assert 'user.not_found:id:3' in rv['messages']


@bolitest(before=set_up)
def test_update_book(client):
    user2 = create_mock(2, 'user', 'register')
    book5 = set_owner(create_mock(1, 'book'), 2)

    rv = client.put('/book/1', book5)
    assert rv['code'] == 200
    assert_equal_books(rv['data'], book5, user2)


@bolitest(before=set_up)
def test_update_book_not_found(client):
    rv = client.put('/book/4', {'name': 'new book name'})
    assert rv['code'] == 404


@bolitest(before=set_up)
def test_partial_update_book(client):
    rv = client.put('/book/1', {'name': 'new book name'})
    assert rv['code'] == 200
    assert rv['data']['name'] == 'new book name'


@bolitest(before=set_up)
def test_partial_update_book_bad_request(client):
    rv = client.put('/book/1', {'name': ''})
    assert rv['code'] == 400
    assert 'param.required:name' in rv['messages']


@bolitest(before=set_up)
def test_update_book_user_not_found(client):
    rv = client.put('/book/1', {'owner_id': 3})
    assert rv['code'] == 404
    assert 'user.not_found:id:3' in rv['messages']


@bolitest(before=set_up)
def test_delete_book(client):
    rv = client.delete('/book/1')
    assert rv['code'] == 200

    rv = client.get('/book/1')
    assert rv['code'] == 404


@bolitest(before=set_up)
def test_delete_book_not_found(client):
    rv = client.delete('/book/4')
    assert rv['code'] == 404