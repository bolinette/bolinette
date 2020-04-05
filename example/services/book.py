from bolinette.services import HistorizedService
from example.models import Book


class BookService(HistorizedService):
    def __init__(self):
        super().__init__(Book)


book_service = BookService()
