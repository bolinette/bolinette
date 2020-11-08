from bolinette import web
from bolinette.decorators import controller


@controller('book', '/book')
class BookController(web.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(),
            self.defaults.get_one('complete'),
            self.defaults.create('complete', access=web.AccessToken.Required),
            self.defaults.update('complete', access=web.AccessToken.Required),
            self.defaults.patch('complete', access=web.AccessToken.Required),
            self.defaults.delete('complete', access=web.AccessToken.Required)
        ]
