from typing import Optional

# noinspection PyUnresolvedReferences
from bolinette.testing.fixture import client
from bolinette.testing import Mock, bolitest, Mocked


def assert_tags_equal(t1s, t2s):
    if not isinstance(t1s, list):
        t1s = [t1s]
    if not isinstance(t2s, list):
        t2s = [t2s]
    assert len(t1s) == len(t2s)
    t1_n = {t['name']: (t['children'] if 'children' in t else None) for t in t1s}
    t2_n = {t['name']: (t['children'] if 'children' in t else None) for t in t2s}
    for name in t1_n:
        assert name in t2_n
    for name in t1_n:
        c1 = t1_n[name]
        c2 = t2_n[name]
        if c1 is None or c2 is None:
            assert c1 == c2
        if c1 is not None and c2 is not None:
            assert_tags_equal(c1, c2)


def set_parent_id(tag: Mocked, parent_id: Optional[int]) -> Mocked:
    tag['parent_id'] = parent_id
    return tag


async def tags_setup(mock: Mock):
    await set_parent_id(mock(1, 'tag'), None).insert()
    await set_parent_id(mock(2, 'tag'), None).insert()
    await set_parent_id(mock(3, 'tag'), None).insert()
    await set_parent_id(mock(4, 'tag'), 1).insert()
    await set_parent_id(mock(5, 'tag'), 2).insert()
    await set_parent_id(mock(6, 'tag'), 4).insert()


@bolitest(before=tags_setup)
async def test_get_tags(client):
    rv = await client.get('/tag')
    assert rv['code'] == 200
    assert len(rv['data']) == 6
    for i in range(6):
        tag = client.mock(i + 1, 'tag')
        assert rv['data'][i]['name'] == tag['name']


@bolitest(before=tags_setup)
async def test_get_tag(client):
    tag1 = client.mock(1, 'tag')
    tag4 = client.mock(4, 'tag')
    tag6 = client.mock(6, 'tag')
    tag4['children'] = [tag6]
    tag1['children'] = [tag4]

    rv = await client.get(f'/tag/{tag1["name"]}')
    assert rv['code'] == 200
    assert_tags_equal(rv['data'], tag1)
