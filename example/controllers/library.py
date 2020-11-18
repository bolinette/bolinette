from bolinette import web
from bolinette.decorators import controller


@controller('library')
class LibraryController(web.Controller):
    def default_routes(self):
        return [
            self.defaults.create(),
            self.defaults.get_all(),
            self.defaults.get_one(key='key')
        ]
