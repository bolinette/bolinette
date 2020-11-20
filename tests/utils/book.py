from bolinette.testing import Mocked, Mock
from tests import utils


def set_author(book: Mocked, author_id: int) -> Mocked:
    book['author_id'] = author_id
    return book


async def set_up(mock: Mock):
    await utils.user.salt_password(mock(1, 'user')).insert()
    await utils.user.salt_password(mock(2, 'user')).insert()
    await mock(1, 'person').insert()
    await mock(2, 'person').insert()
    await set_author(mock(1, 'book'), 1).insert()
    await set_author(mock(2, 'book'), 1).insert()
    await set_author(mock(3, 'book'), 2).insert()
