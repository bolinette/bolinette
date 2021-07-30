from typing import Optional

# noinspection PyUnresolvedReferences
from bolinette.testing.fixture import client
from bolinette.testing import Mock, bolitest, Mocked, BolitestClient


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


def set_tag_attrs(tag: Mocked, parent_id: Optional[int]) -> Mocked:
    tag['parent_id'] = parent_id
    return tag


def set_label_attrs(label: Mocked, label_id: int, tag_id: Optional[int]) -> Mocked:
    label['id'] = label_id
    label['tag_id'] = tag_id
    return label


async def tags_setup(mock: Mock):
    await set_tag_attrs(mock(1, 'tag'), None).insert()
    await set_tag_attrs(mock(2, 'tag'), None).insert()
    await set_tag_attrs(mock(3, 'tag'), None).insert()
    await set_tag_attrs(mock(4, 'tag'), 1).insert()
    await set_tag_attrs(mock(5, 'tag'), 2).insert()
    await set_tag_attrs(mock(6, 'tag'), 4).insert()


async def labels_setup(mock: Mock):
    await set_tag_attrs(mock(1, 'tag'), None).insert()
    await set_tag_attrs(mock(2, 'tag'), None).insert()
    await set_label_attrs(mock(1, 'label'), 1, 1).insert()
    await set_label_attrs(mock(2, 'label'), 2, 1).insert()
    await set_label_attrs(mock(3, 'label'), 1, 2).insert()


@bolitest(before=tags_setup)
async def test_get_tags(client: BolitestClient):
    rv = await client.get('/tag')
    assert rv['code'] == 200
    assert len(rv['data']) == 6
    for i in range(6):
        tag = client.mock(i + 1, 'tag')
        assert rv['data'][i]['name'] == tag['name']


@bolitest(before=tags_setup)
async def test_get_tag(client: BolitestClient):
    tag1 = client.mock(1, 'tag')
    tag4 = client.mock(4, 'tag')
    tag6 = client.mock(6, 'tag')
    tag4['children'] = [tag6]
    tag1['children'] = [tag4]

    rv = await client.get(f'/tag/{tag1["name"]}')
    assert rv['code'] == 200
    assert_tags_equal(rv['data'], tag1)


@bolitest()
async def test_create_tag(client: BolitestClient):
    tag1 = client.mock(1, 'tag')

    rv = await client.post('/tag', tag1.to_payload())
    assert rv['code'] == 201


@bolitest()
async def test_create_tags(client: BolitestClient):
    tag1 = client.mock(1, 'tag')
    tag11 = client.mock(11, 'tag')
    tag12 = client.mock(12, 'tag')
    tag121 = client.mock(121, 'tag')

    rv = await client.post('/tag', tag1.to_payload())
    assert rv['code'] == 201
    tag11['parent_id'] = rv['data']['id']
    tag12['parent_id'] = rv['data']['id']
    rv = await client.post('/tag', tag11.to_payload())
    assert rv['code'] == 201
    rv = await client.post('/tag', tag12.to_payload())
    assert rv['code'] == 201
    tag121['parent_id'] = rv['data']['id']
    rv = await client.post('/tag', tag121.to_payload())
    assert rv['code'] == 201

    rv = await client.get(f'/tag/{tag1["name"]}')
    tag12['children'] = [tag121]
    tag1['children'] = [tag11, tag12]
    assert_tags_equal(rv['data'], tag1)


@bolitest(before=labels_setup)
async def test_get_tag_labels(client: BolitestClient):
    tag1 = client.mock(1, 'tag')

    rv = await client.get(f'/tag/{tag1["name"]}')
    assert len(rv['data']['labels']) == 2
    assert len([label for label in rv['data']['labels'] if label['id'] == 1]) == 1
    assert len([label for label in rv['data']['labels'] if label['id'] == 2]) == 1


@bolitest(before=labels_setup)
async def test_get_label(client: BolitestClient):
    tag1 = client.mock(1, 'tag')
    label1 = client.mock(1, 'label')

    rv = await client.get(f'/label/{tag1["name"]}/1')
    assert rv['code'] == 200
    assert rv['data']['tag']['name'] == tag1['name']
    assert rv['data']['name'] == label1['name']


@bolitest(before=labels_setup)
async def test_get_label_not_found(client: BolitestClient):
    tag1 = client.mock(1, 'tag')

    rv = await client.get(f'/label/{tag1["name"]}/3')
    assert rv['code'] == 404
    assert f'entity.not_found:label:tag.name,id:{tag1["name"]},3'

    rv = await client.get('/label/non_existing_tag/1')
    assert rv['code'] == 404
    assert 'entity.not_found:label:tag.name,id:non_existing_tag,1'
