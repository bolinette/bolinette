from bolinette.data import service, Service

from example.entities import Book


@service("book")
class BookService(Service[Book]):
    async def get_books_over_650_pages(self):
        return await self.repo.query().filter(lambda b: b.pages >= 650).all()

    async def get_books_under_700_pages(self):
        return await self.repo.query().filter(lambda b: b.pages <= 700).all()
