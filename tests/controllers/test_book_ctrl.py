from datetime import datetime

from dateutil import parser as date_parser

from bolinette.testing import bolitest, Mock
# noinspection PyUnresolvedReferences
from bolinette.testing.fixture import client
from tests import utils
# noinspection PyUnresolvedReferences
import example.models


async def big_set_up(mock: Mock):
    await mock(1, 'person').insert()
    for i in range(100):
        await utils.book.insert_book(mock(i, 'book'), 1)


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
        assert equal_books(rv['data'][i], client.mock(i, 'book').to_response())


@bolitest(before=utils.book.set_up)
async def test_get_book(client):
    author1 = client.mock(1, 'person')
    book1 = utils.book.create_book(client.mock, 1, 1)

    rv = await client.get(f'/book/{book1["uid"]}')
    assert rv['code'] == 200
    assert equal_books(rv['data'], book1.to_response(), author1.to_response())


@bolitest(before=utils.book.set_up)
async def test_get_book2(client):
    author2 = client.mock(2, 'person')
    book3 = utils.book.create_book(client.mock, 3, 2)

    rv = await client.get(f'/book/{book3["uid"]}')
    assert rv['code'] == 200
    assert equal_books(rv['data'], book3.to_response(), author2.to_response())


@bolitest(before=utils.book.set_up)
async def test_get_book_not_found(client):
    rv = await client.get('/book/4')
    assert rv['code'] == 404


@bolitest(before=utils.book.set_up)
async def test_create_book(client):
    author1 = client.mock(1, 'person')
    book4 = utils.book.create_book(client.mock, 4, 1)
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.post('/book', book4.to_payload())
    assert rv['code'] == 201
    assert equal_books(rv['data'], book4.to_response(), author1.to_response())
    assert rv['data']['created_by']['username'] == user1['username']
    assert rv['data']['updated_by']['username'] == user1['username']


@bolitest(before=utils.book.set_up)
async def test_create_book_bad_request(client):
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.post('/book', {})
    assert rv['code'] == 422
    assert 'param.required:name' in rv['messages']
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:author' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_create_book_author_not_found(client):
    author3 = client.mock(3, 'person')
    book4 = utils.book.create_book(client.mock, 4, 3)
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.post('/book', book4.to_payload())
    assert rv['code'] == 404
    assert f'entity.not_found:person:uid:{author3["uid"]}' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_historized_entities(client):
    user1 = client.mock(1, 'user')
    user2 = client.mock(2, 'user')
    book4 = utils.book.create_book(client.mock, 4, 1)

    await client.post('/user/login', user1.to_payload('login'))
    t_before_create = datetime.utcnow()
    await client.post('/book', book4.to_payload())
    t_after_create = datetime.utcnow()
    book4['name'] = 'new name'
    await client.post('/user/login', user2.to_payload('login'))

    t_before_update = datetime.utcnow()
    rv = await client.put(f'/book/{book4["uid"]}', book4.to_payload())
    assert rv['code'] == 200
    t_after_update = datetime.utcnow()
    assert rv['data']['created_by']['username'] == user1['username']
    assert rv['data']['updated_by']['username'] == user2['username']
    created_on = date_parser.parse(rv['data']['created_on'])
    updated_on = date_parser.parse(rv['data']['updated_on'])
    assert t_before_create < created_on < t_after_create
    assert t_before_update < updated_on < t_after_update


@bolitest(before=utils.book.set_up)
async def test_update_book(client):
    author2 = client.mock(2, 'person')
    book1 = utils.book.create_book(client.mock, 1, 2)
    user2 = client.mock(2, 'user')

    await client.post('/user/login', user2.to_payload('login'))

    rv = await client.put(f'/book/{book1["uid"]}', book1.to_payload())
    assert rv['code'] == 200
    assert equal_books(rv['data'], book1.to_response(), author2.to_response())
    assert rv['data']['updated_by']['username'] == user2['username']


@bolitest(before=utils.book.set_up)
async def test_update_book_bad_request(client):
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.put('/book/1', {'name': 'new book name'})
    assert rv['code'] == 422
    assert 'param.required:pages' in rv['messages']
    assert 'param.required:author' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_update_book_not_found(client):
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.patch('/book/4', {'name': 'new book name'})
    assert rv['code'] == 404


@bolitest(before=utils.book.set_up)
async def test_patch_book(client):
    author1 = client.mock(1, 'person')
    book1 = utils.book.create_book(client.mock, 1, 1)
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.patch(f'/book/{book1["uid"]}', {'name': 'new book name'})
    assert rv['code'] == 200
    assert rv['data']['name'] == 'new book name'
    assert rv['data']['pages'] == book1['pages']
    assert rv['data']['author']['full_name'] == author1.to_response()['full_name']


@bolitest(before=utils.book.set_up)
async def test_patch_book_bad_request(client):
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.patch('/book/1', {'name': ''})
    assert rv['code'] == 422
    assert 'param.non_nullable:name' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_update_book_author_not_found(client):
    user1 = client.mock(1, 'user')
    book1 = client.mock(1, 'book')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.patch(f'/book/{book1["uid"]}', {'author': {'uid': 'unknown'}})
    assert rv['code'] == 404
    assert 'entity.not_found:person:uid:unknown' in rv['messages']


@bolitest(before=utils.book.set_up)
async def test_delete_book(client):
    user1 = client.mock(1, 'user')
    book1 = client.mock(1, 'book')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.delete(f'/book/{book1["uid"]}')
    assert rv['code'] == 200

    rv = await client.get(f'/book/{book1["uid"]}')
    assert rv['code'] == 404


@bolitest(before=utils.book.set_up)
async def test_delete_book_not_found(client):
    user1 = client.mock(1, 'user')

    await client.post('/user/login', user1.to_payload('login'))

    rv = await client.delete('/book/4')
    assert rv['code'] == 404
