from bolinette.testing import Mocked, mock
from example.models import Person, Book
from tests import utils


def set_author(book: Mocked, author_id: int) -> Mocked:
    book.fields.author_id = author_id
    return book


def set_up():
    utils.user.salt_password(mock(1, 'user')).insert(User)
    utils.user.salt_password(mock(2, 'user')).insert(User)
    mock(1, 'person').insert(Person)
    mock(2, 'person').insert(Person)
    set_author(mock(1, 'book'), 1).insert(Book)
    set_author(mock(2, 'book'), 1).insert(Book)
    set_author(mock(3, 'book'), 2).insert(Book)
