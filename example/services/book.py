from bolinette.services import BaseService
from example.models import Book


class BookService(BaseService):
    def __init__(self):
        super().__init__(Book, 'book')


book_service = BookService()
