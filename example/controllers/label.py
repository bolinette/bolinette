from bolinette.web import Controller, controller


@controller("label")
class LabelController(Controller):
    def default_routes(self):
        return [
            self.defaults.get_one("complete", key=["tag.name", "id"]),
            self.defaults.get_all(),
            self.defaults.create(),
            self.defaults.update(key=["tag.name", "id"]),
            self.defaults.delete(key=["tag.name", "id"]),
        ]
