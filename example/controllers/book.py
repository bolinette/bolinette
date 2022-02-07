from bolinette.core import BolinetteContext
from bolinette.web import WebContext, Controller, controller, route, Returns
from example.services import BookService


@controller("book", "/book", middlewares=["auth"])
class BookController(Controller):
    def __init__(
        self, context: BolinetteContext, web_ctx: WebContext, book_service: BookService
    ):
        super().__init__(context, web_ctx)
        self.book_service = book_service

    def default_routes(self):
        return [
            self.defaults.get_all(middlewares=["!auth"]),
            self.defaults.get_one("complete", middlewares=["!auth"]),
            self.defaults.create("complete"),
            self.defaults.update("complete"),
            self.defaults.patch("complete"),
            self.defaults.delete("complete"),
        ]

    @route.get(
        "/pages+650", returns=Returns("book", as_list=True), middlewares=["!auth"]
    )
    async def get_books_over_650_pages(self):
        return self.response.ok(data=await self.book_service.get_books_over_650_pages())

    @route.get(
        "/pages-700", returns=Returns("book", as_list=True), middlewares=["!auth"]
    )
    async def get_books_under_700_pages(self):
        return self.response.ok(
            data=await self.book_service.get_books_under_700_pages()
        )
