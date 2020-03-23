from bolinette.testing import client, bolitest, create_mock, insert

from example.models import Book, Person


def set_author(book, author_id):
    book['author_id'] = author_id
    return book


def set_up():
    insert(Person, create_mock(1, 'person'))
    insert(Person, create_mock(2, 'person'))
    insert(Book, set_author(create_mock(1, 'book'), 1))
    insert(Book, set_author(create_mock(2, 'book'), 1))
    insert(Book, set_author(create_mock(3, 'book'), 2))


@bolitest(before=set_up)
async def test_get_person(client):
    person1 = create_mock(1, 'person')

    rv = await client.get('/person/1')
    assert rv['code'] == 200
    assert rv['data']['name'] == person1['name']
    assert len(rv['data']['books']) == 2
