from bolinette import core, blnt
from bolinette.decorators import service


@service('book')
class BookService(core.HistorizedService):
    def __init__(self, context: 'blnt.BolinetteContext'):
        super().__init__(context)

    async def get_books_over_650_pages(self):
        return await self.repo.query().filter(lambda b: b.pages >= 650).all()

    async def get_books_under_700_pages(self):
        return await self.repo.query().filter(lambda b: b.pages <= 700).all()
