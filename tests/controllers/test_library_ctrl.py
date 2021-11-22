from bolinette.testing import Mock, bolitest
from bolinette.testing.fixture import client
import example.models


async def set_up(mock: Mock):
    await mock(1, 'library').insert()
    await mock(2, 'library').insert()
    await mock(3, 'library').insert()


def libraries_equal(l1, l2):
    return l1['key'] == l2['key'] and l1['name'] == l2['name'] and l1['address'] == l2['address']


@bolitest(before=set_up)
async def test_get_libraries(client):
    rv = await client.get('/library')
    assert rv['code'] == 200
    assert len(rv['data']) == 3


@bolitest(before=set_up)
async def test_get_one_library(client):
    library2 = client.mock(2, 'library')

    rv = await client.get(f'/library/{library2["key"]}')
    assert rv['code'] == 200
    assert rv['data']['key'] == library2['key']
    assert rv['data']['name'] == library2['name']
    assert rv['data']['address'] == library2['address']


@bolitest(before=set_up)
async def test_get_one_library_not_found(client):
    rv = await client.get('/library/unknown_key')
    assert rv['code'] == 404
    assert 'entity.not_found:library:key:unknown_key' in rv['messages']


@bolitest(before=set_up)
async def test_create_library(client):
    library4 = client.mock(4, 'library')

    rv = await client.post('/library', library4.to_payload())
    assert rv['code'] == 201
    assert rv['data']['key'] == library4['key']
    assert rv['data']['name'] == library4['name']
    assert rv['data']['address'] == library4['address']


@bolitest(before=set_up)
async def test_create_library_and_get(client):
    library4 = client.mock(4, 'library')

    await client.post('/library', library4.to_payload())

    rv = await client.get(f'/library/{library4["key"]}')
    assert rv['code'] == 200
    assert rv['data']['key'] == library4['key']
    assert rv['data']['name'] == library4['name']
    assert rv['data']['address'] == library4['address']


@bolitest(before=set_up)
async def test_create_library_bad_request(client):
    rv = await client.post('/library', {})
    assert rv['code'] == 422
    assert 'param.required:key' in rv['messages']
    assert 'param.required:name' in rv['messages']


@bolitest(before=set_up)
async def test_create_library_conflict(client):
    library1 = client.mock(1, 'library')
    library4 = client.mock(4, 'library')
    library4['key'] = library1['key']

    rv = await client.post('/library', library4.to_payload())
    assert rv['code'] == 409
    assert f'param.conflict:key:{library1["key"]}' in rv['messages']


@bolitest(before=set_up)
async def test_update_library(client):
    library1 = client.mock(1, 'library')
    key = library1['key']
    library1['key'] = 'new_library_key'
    library1['name'] = 'New Library Name'
    library1['address'] = 'New Library Address'

    rv = await client.put(f'/library/{key}', library1.to_response())
    assert rv['code'] == 200
    assert libraries_equal(library1, rv['data'])


@bolitest(before=set_up)
async def test_update_library_and_get(client):
    library1 = client.mock(1, 'library')
    key = library1['key']
    library1['key'] = 'new_library_key'
    library1['name'] = 'New Library Name'
    library1['address'] = 'New Library Address'

    rv = await client.put(f'/library/{key}', library1.to_response())
    assert rv['code'] == 200

    rv = await client.get('/library/new_library_key')
    assert rv['code'] == 200
    assert libraries_equal(library1, rv['data'])


@bolitest(before=set_up)
async def test_update_library_bad_request(client):
    library1 = client.mock(1, 'library')

    rv = await client.put(f'/library/{library1["key"]}', {})
    assert rv['code'] == 422
    assert 'param.required:key' in rv['messages']
    assert 'param.required:name' in rv['messages']


@bolitest(before=set_up)
async def test_update_library_conflict(client):
    library1 = client.mock(1, 'library')
    library2 = client.mock(2, 'library')

    rv = await client.put(f'/library/{library1["key"]}', library2.to_payload())
    assert rv['code'] == 409
    assert f'param.conflict:key:{library2["key"]}' in rv['messages']


@bolitest(before=set_up)
async def test_patch_library(client):
    library1 = client.mock(1, 'library')
    library1['name'] = 'New Library Name'

    rv = await client.patch(f'/library/{library1["key"]}', {'name': library1['name']})
    assert rv['code'] == 200
    assert libraries_equal(library1, rv['data'])


@bolitest(before=set_up)
async def test_patch_library_bad_request(client):
    library1 = client.mock(1, 'library')

    rv = await client.patch(f'/library/{library1["key"]}', {'name': None})
    assert rv['code'] == 422
    assert 'param.non_nullable:name' in rv['messages']


@bolitest(before=set_up)
async def test_patch_library_conflict(client):
    library1 = client.mock(1, 'library')
    library2 = client.mock(2, 'library')

    rv = await client.patch(f'/library/{library1["key"]}', {'key': library2['key']})
    assert rv['code'] == 409
    assert f'param.conflict:key:{library2["key"]}' in rv['messages']


@bolitest(before=set_up)
async def test_delete_library(client):
    library1 = client.mock(1, 'library')

    rv = await client.delete(f'/library/{library1["key"]}')
    assert rv['code'] == 200
    assert libraries_equal(library1, rv['data'])


@bolitest(before=set_up)
async def test_delete_library_not_found(client):
    rv = await client.delete('/library/unknown_key')
    assert rv['code'] == 404
