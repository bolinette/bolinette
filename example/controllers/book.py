from bolinette import data, types
from bolinette.decorators import controller


@controller('book', '/book')
class BookController(data.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(),
            self.defaults.get_one('complete'),
            self.defaults.create('complete', access=types.web.AccessToken.Required),
            self.defaults.update('complete', access=types.web.AccessToken.Required),
            self.defaults.patch('complete', access=types.web.AccessToken.Required),
            self.defaults.delete('complete', access=types.web.AccessToken.Required)
        ]
