from bolinette.testing import Mock, bolitest, TestClient


async def set_up(mock: Mock):
    await mock(1, 'library').insert()
    await mock(2, 'library').insert()
    await mock(3, 'library').insert()


@bolitest(before=set_up)
async def test_get_libraries(client: TestClient):
    rv = await client.get('/library')
    assert rv['code'] == 200
    assert len(rv['data']) == 3


@bolitest(before=set_up)
async def test_get_one_library(client: TestClient):
    library2 = client.mock(2, 'library')

    rv = await client.get(f'/library/{library2["key"]}')
    assert rv['code'] == 200
    assert rv['data']['key'] == library2['key']
    assert rv['data']['name'] == library2['name']
    assert rv['data']['address'] == library2['address']


@bolitest(before=set_up)
async def test_get_one_library_not_found(client: TestClient):
    rv = await client.get('/library/unknown_key')
    assert rv['code'] == 404
    assert 'entity.not_found:library:key:unknown_key' in rv['messages']


@bolitest(before=set_up)
async def test_create_library(client: TestClient):
    library4 = client.mock(4, 'library')

    rv = await client.post('/library', library4.to_payload())
    assert rv['code'] == 201
    assert rv['data']['key'] == library4['key']
    assert rv['data']['name'] == library4['name']
    assert rv['data']['address'] == library4['address']


@bolitest(before=set_up)
async def test_create_library_and_get(client: TestClient):
    library4 = client.mock(4, 'library')

    await client.post('/library', library4.to_payload())

    rv = await client.get(f'/library/{library4["key"]}')
    assert rv['code'] == 200
    assert rv['data']['key'] == library4['key']
    assert rv['data']['name'] == library4['name']
    assert rv['data']['address'] == library4['address']
