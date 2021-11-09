from bolinette.testing import Mocked, Mock
from tests import utils


async def insert_book(book: Mocked, author_id: int, user_id: int):
    book['author_id'] = author_id
    book['created_by_id'] = user_id
    book['updated_by_id'] = user_id
    await book.insert()


async def insert_person(person: Mocked, user_id: int):
    person['created_by_id'] = user_id
    person['updated_by_id'] = user_id
    await person.insert()


def create_book(mock: Mock, book_id: int, author_id: int) -> Mocked:
    author = mock(author_id, 'person')
    book = mock(book_id, 'book')
    book['author_id'] = author_id
    book['author'] = author.fields
    return book


async def set_up(mock: Mock):
    await utils.user.salt_password(mock(1, 'user')).insert()
    await utils.user.salt_password(mock(2, 'user')).insert()
    await insert_person(mock(1, 'person'), 1)
    await insert_person(mock(2, 'person'), 1)
    await insert_book(mock(1, 'book'), 1, 1)
    await insert_book(mock(2, 'book'), 1, 1)
    await insert_book(mock(3, 'book'), 2, 1)
