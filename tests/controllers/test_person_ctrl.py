from bolinette.testing import bolitest, TestClient
from tests import utils
import example


@bolitest(before=utils.book.set_up)
async def test_get_person(client: TestClient):
    person1 = client.mock(1, 'person')

    rv = await client.get('/person/1')
    person1_res = person1.to_response()
    assert rv['code'] == 200
    assert rv['data']['first_name'] == person1_res['first_name']
    assert rv['data']['last_name'] == person1_res['last_name']
    assert rv['data']['full_name'] == person1_res['full_name']
    assert len(rv['data']['books']) == 2
