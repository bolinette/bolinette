from bolinette.testing import Mocked, Mock
from tests import utils


async def insert_book(book: Mocked, author_id: int):
    book['author_id'] = author_id
    await book.insert()


def create_book(mock: Mock, book_id: int, author_id: int) -> Mocked:
    author = mock(author_id, 'person')
    book = mock(book_id, 'book')
    book['author_id'] = author_id
    book['author'] = author.fields
    return book


async def set_up(mock: Mock):
    await utils.user.salt_password(mock(1, 'user')).insert()
    await utils.user.salt_password(mock(2, 'user')).insert()
    await mock(1, 'person').insert()
    await mock(2, 'person').insert()
    await insert_book(mock(1, 'book'), 1)
    await insert_book(mock(2, 'book'), 1)
    await insert_book(mock(3, 'book'), 2)
