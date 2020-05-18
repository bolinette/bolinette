from bolinette.testing import Mocked, Mock
from tests import utils


def set_author(book: Mocked, author_id: int) -> Mocked:
    book.fields.author_id = author_id
    return book


async def set_up(_, mock: Mock):
    utils.user.salt_password(mock(1, 'user')).insert()
    utils.user.salt_password(mock(2, 'user')).insert()
    mock(1, 'person').insert()
    mock(2, 'person').insert()
    set_author(mock(1, 'book'), 1).insert()
    set_author(mock(2, 'book'), 1).insert()
    set_author(mock(3, 'book'), 2).insert()
