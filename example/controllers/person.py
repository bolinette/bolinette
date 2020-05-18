from bolinette import data
from bolinette.decorators import controller


@controller('person', '/person')
class PersonController(data.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(),
            self.defaults.get_one('complete'),
            self.defaults.create('complete'),
            self.defaults.update('complete'),
            self.defaults.patch('complete'),
            self.defaults.delete('complete')
        ]
