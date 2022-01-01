from bolinette.web import Controller, controller


@controller('library')
class LibraryController(Controller):
    def default_routes(self):
        return [
            self.defaults.create(),
            self.defaults.get_all(),
            self.defaults.get_one(key='key'),
            self.defaults.update(key='key'),
            self.defaults.patch(key='key'),
            self.defaults.delete(key='key')
        ]
