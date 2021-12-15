from bolinette import data, core
from bolinette.decorators import service


@service('book')
class BookService(data.Service):
    def __init__(self, context: 'core.BolinetteContext'):
        super().__init__(context)

    async def get_books_over_650_pages(self):
        return await self.repo.query().filter(lambda b: b.pages >= 650).all()

    async def get_books_under_700_pages(self):
        return await self.repo.query().filter(lambda b: b.pages <= 700).all()
