from bolinette import blnt
from bolinette.decorators import controller


@controller('role', '/role')
class RoleController(blnt.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(roles=['admin']),
            self.defaults.get_one('complete', key='name', roles=['admin'])
        ]
