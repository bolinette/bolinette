import pytest

from bolinette.testing import client, bolitest, create_mock, insert

from example.models import Book, Person


def set_author(mock, author_id):
    mock['author_id'] = author_id
    return mock


def set_up():
    insert(Person, create_mock(1, 'person'))
    insert(Person, create_mock(2, 'person'))
    insert(Book, set_author(create_mock(1, 'book'), 1))
    insert(Book, set_author(create_mock(2, 'book'), 1))
    insert(Book, set_author(create_mock(3, 'book'), 2))


def big_set_up():
    insert(Person, create_mock(1, 'person'))
    for i in range(100):
        insert(Book, set_author(create_mock(i, 'book'), 1))


def equal_books(b1, b2, author=None):
    return (b1['name'] == b2['name']
            and b1['pages'] == b2['pages']
            and b1['author']['name'] == author['name'] if author is not None else True)


@bolitest(before=set_up)
def test_get_books(client):
    rv = client.get('/book')
    assert rv['code'] == 200
    assert len(rv['data']) == 3


@bolitest(before=big_set_up)
def test_get_books_paginated(client):
    rv = client.get('/book?page=1')
    assert rv['code'] == 200
    assert len(rv['data']) == 20
    assert rv['pagination']['page'] == 1
    assert rv['pagination']['per_page'] == 20
    assert rv['pagination']['total'] == 100
    for i in range(20):
        assert equal_books(rv['data'][i], create_mock(i, 'book'))


@bolitest(before=set_up)
def test_get_book(client):
    author1 = create_mock(1, 'person')
    book1 = set_author(create_mock(1, 'book'), 1)

    rv = client.get('/book/1')
    assert rv['code'] == 200
    assert equal_books(rv['data'], book1, author1)


@bolitest(before=set_up)
def test_get_book2(client):
    author2 = create_mock(2, 'person')
    book3 = set_author(create_mock(3, 'book'), 2)

    rv = client.get('/book/3')
    assert rv['code'] == 200
    assert equal_books(rv['data'], book3, author2)


@bolitest(before=set_up)
def test_get_book_not_found(client):
    rv = client.get('/book/4')
    assert rv['code'] == 404


@bolitest(before=set_up)
def test_create_book(client):
    author1 = create_mock(1, 'person')
    book4 = set_author(create_mock(4, 'book'), 1)

    rv = client.post('/book', book4)
    assert rv['code'] == 201
    assert equal_books(rv['data'], book4, author1)


@bolitest(before=set_up)
def test_create_book_bad_request(client):
    rv = client.post('/book', {})
    assert rv['code'] == 400
    assert 'param.required:name' in rv['messages']
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:author_id' in rv['messages']


@bolitest(before=set_up)
def test_create_book_author_not_found(client):
    book4 = set_author(create_mock(4, 'book'), 3)

    rv = client.post('/book', book4)
    assert rv['code'] == 404
    assert 'person.not_found:id:3' in rv['messages']


@bolitest(before=set_up)
def test_update_book(client):
    author2 = create_mock(2, 'person')
    book1 = set_author(create_mock(1, 'book'), 2)

    rv = client.put('/book/1', book1)
    assert rv['code'] == 200
    assert equal_books(rv['data'], book1, author2)


@bolitest(before=set_up)
def test_update_book_bad_request(client):
    rv = client.put('/book/1', {'name': 'new book name'})
    assert rv['code'] == 400
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:author_id' in rv['messages']


@bolitest(before=set_up)
def test_update_book_not_found(client):
    rv = client.patch('/book/4', {'name': 'new book name'})
    assert rv['code'] == 404


@bolitest(before=set_up)
def test_patch_book(client):
    author1 = create_mock(1, 'person')
    book1 = set_author(create_mock(1, 'book'), 1)

    rv = client.patch('/book/1', {'name': 'new book name'})
    assert rv['code'] == 200
    assert rv['data']['name'] == 'new book name'
    assert rv['data']['pages'] == book1['pages']
    assert rv['data']['author']['name'] == author1['name']


@bolitest(before=set_up)
def test_patch_book_bad_request(client):
    rv = client.patch('/book/1', {'name': ''})
    assert rv['code'] == 400
    assert 'param.required:name' in rv['messages']


@bolitest(before=set_up)
def test_update_book_author_not_found(client):
    rv = client.patch('/book/1', {'author_id': 3})
    assert rv['code'] == 404
    assert 'person.not_found:id:3' in rv['messages']


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
