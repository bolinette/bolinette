from bolinette import web
from bolinette.decorators import controller


@controller('tag')
class TagController(web.Controller):
    def default_routes(self):
        return [
            self.defaults.get_one('complete', key='name'),
            self.defaults.get_all(),
            self.defaults.create(),
            self.defaults.update(),
            self.defaults.delete()
        ]
