from bolinette.web import Controller, controller


@controller('tag')
class TagController(Controller):
    def default_routes(self):
        return [
            self.defaults.get_one('complete', key='name'),
            self.defaults.get_all(),
            self.defaults.create(),
            self.defaults.update(),
            self.defaults.delete()
        ]
