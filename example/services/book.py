from bolinette.services import HistorizedService


class BookService(HistorizedService):
    def __init__(self):
        super().__init__('book')


book_service = BookService()
