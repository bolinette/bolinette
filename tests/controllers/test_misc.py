from bolinette.testing import TestClient, bolitest
# noinspection PyUnresolvedReferences
from bolinette.testing.fixture import client


@bolitest()
async def test_hello_no_param(client: TestClient):
    rv = await client.get('/hello', prefix='')
    assert rv['code'] == 200
    assert rv['data'] == 'Hello user!'


@bolitest()
async def test_hello_param(client: TestClient):
    rv = await client.get('/hello/bob', prefix='')
    assert rv['code'] == 200
    assert rv['data'] == 'Hello bob!'
