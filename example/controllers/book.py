from bolinette import abc, web
from bolinette.decorators import controller, get
from example.services import BookService


@controller('book', '/book', middlewares=['auth'])
class BookController(web.Controller):
    def __init__(self, context: abc.Context, book_service: BookService):
        super().__init__(context)
        self.book_service = book_service

    def default_routes(self):
        return [
            self.defaults.get_all(middlewares=['!auth']),
            self.defaults.get_one('complete', middlewares=['!auth']),
            self.defaults.create('complete'),
            self.defaults.update('complete'),
            self.defaults.patch('complete'),
            self.defaults.delete('complete')
        ]

    @get('/pages+650', returns=web.Returns('book', as_list=True), middlewares=['!auth'])
    async def get_books_over_650_pages(self):
        return self.response.ok(data=await self.book_service.get_books_over_650_pages())

    @get('/pages-700', returns=web.Returns('book', as_list=True), middlewares=['!auth'])
    async def get_books_under_700_pages(self):
        return self.response.ok(data=await self.book_service.get_books_under_700_pages())
