from bolinette.testing import bolitest, BolitestClient
# noinspection PyUnresolvedReferences
from bolinette.testing.fixture import client
from tests import utils
# noinspection PyUnresolvedReferences
import example.models


@bolitest(before=utils.book.set_up)
async def test_get_person(client: BolitestClient):
    person1 = client.mock(1, 'person')

    rv = await client.get(f'/person/{person1["uid"]}')
    person1_res = person1.to_response()
    assert rv['code'] == 200
    assert rv['data']['first_name'] == person1_res['first_name']
    assert rv['data']['last_name'] == person1_res['last_name']
    assert rv['data']['full_name'] == person1_res['full_name']
    assert len(rv['data']['books']) == 2


@bolitest(before=utils.book.set_up)
async def test_get_person_books(client: BolitestClient):
    person1 = client.mock(1, 'person')
    book1 = client.mock(1, 'book')
    book2 = client.mock(2, 'book')

    rv = await client.get(f'/person/{person1["uid"]}')
    assert rv['code'] == 200
    assert len(rv['data']['books']) == 2
    assert any((b for b in rv['data']['books'] if b['uid'] == book1['uid']))
    assert any((b for b in rv['data']['books'] if b['uid'] == book2['uid']))
    assert (rv['data']['last_book']['uid'] ==
            sorted([book1, book2], key=lambda b: b['publication_date'], reverse=True)[0]['uid'])
