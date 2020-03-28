from bolinette.testing import client, bolitest, mock
from tests import utils

from example.models import Book, Person


def big_set_up():
    mock(1, 'person').insert(Person)
    for i in range(100):
        utils.book.set_author(mock(i, 'book'), 1).insert(Book)


def equal_books(b1: dict, b2: dict, author: dict = None):
    return (b1['name'] == b2['name']
            and b1['pages'] == b2['pages']
            and b1['author']['full_name'] == author['full_name'] if author is not None else True)


@bolitest(before=utils.book.set_up)
async def test_get_books(client):
    rv = await client.get('/book')
    assert rv['code'] == 200
    assert len(rv['data']) == 3


@bolitest(before=big_set_up)
async def test_get_books_paginated(client):
    rv = await client.get('/book?page=1')
    assert rv['code'] == 200
    assert len(rv['data']) == 20
    assert rv['pagination']['page'] == 1
    assert rv['pagination']['per_page'] == 20
    assert rv['pagination']['total'] == 100
    for i in range(20):
        assert equal_books(rv['data'][i], mock(i, 'book').to_response())


@bolitest(before=utils.book.set_up)
async def test_get_book(client):
    author1 = mock(1, 'person')
    book1 = utils.book.set_author(mock(1, 'book'), 1)

    rv = await client.get('/book/1')
    assert rv['code'] == 200
    assert equal_books(rv['data'], book1.to_response(), author1.to_response())


@bolitest(before=utils.book.set_up)
async def test_get_book2(client):
    author2 = mock(2, 'person')
    book3 = utils.book.set_author(mock(3, 'book'), 2)

    rv = await client.get('/book/3')
    assert rv['code'] == 200
    assert equal_books(rv['data'], book3.to_response(), author2.to_response())


@bolitest(before=utils.book.set_up)
async def test_get_book_not_found(client):
    rv = await client.get('/book/4')
    assert rv['code'] == 404


@bolitest(before=utils.book.set_up)
async def test_create_book(client):
    author1 = mock(1, 'person')
    book4 = utils.book.set_author(mock(4, 'book'), 1)

    rv = await client.post('/book', book4.to_payload())
    assert rv['code'] == 201
    assert equal_books(rv['data'], book4.to_response(), author1.to_response())


@bolitest(before=utils.book.set_up)
async def test_create_book_bad_request(client):
    rv = await client.post('/book', {})
    assert rv['code'] == 400
    assert 'param.required:name' in rv['messages']
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:author_id' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_create_book_author_not_found(client):
    book4 = utils.book.set_author(mock(4, 'book'), 3)

    rv = await client.post('/book', book4.to_payload())
    assert rv['code'] == 404
    assert 'person.not_found:id:3' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_update_book(client):
    author2 = mock(2, 'person')
    book1 = utils.book.set_author(mock(1, 'book'), 2)

    rv = await client.put('/book/1', book1.to_payload())
    assert rv['code'] == 200
    assert equal_books(rv['data'], book1.to_response(), author2.to_response())


@bolitest(before=utils.book.set_up)
async def test_update_book_bad_request(client):
    rv = await client.put('/book/1', {'name': 'new book name'})
    assert rv['code'] == 400
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:author_id' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_update_book_not_found(client):
    rv = await client.patch('/book/4', {'name': 'new book name'})
    assert rv['code'] == 404


@bolitest(before=utils.book.set_up)
async def test_patch_book(client):
    author1 = mock(1, 'person')
    book1 = utils.book.set_author(mock(1, 'book'), 1)

    rv = await client.patch('/book/1', {'name': 'new book name'})
    assert rv['code'] == 200
    assert rv['data']['name'] == 'new book name'
    assert rv['data']['pages'] == book1.fields.pages
    assert rv['data']['author']['full_name'] == author1.to_response()['full_name']


@bolitest(before=utils.book.set_up)
async def test_patch_book_bad_request(client):
    rv = await client.patch('/book/1', {'name': ''})
    assert rv['code'] == 400
    assert 'param.required:name' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_update_book_author_not_found(client):
    rv = await client.patch('/book/1', {'author_id': 3})
    assert rv['code'] == 404
    assert 'person.not_found:id:3' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_delete_book(client):
    rv = await client.delete('/book/1')
    assert rv['code'] == 200

    rv = await client.get('/book/1')
    assert rv['code'] == 404


@bolitest(before=utils.book.set_up)
async def test_delete_book_not_found(client):
    rv = await client.delete('/book/4')
    assert rv['code'] == 404
