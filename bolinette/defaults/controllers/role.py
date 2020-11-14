from bolinette import web
from bolinette.decorators import controller


@controller('role', '/role')
class RoleController(web.Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(middlewares=['auth|roles=admin']),
            self.defaults.get_one('complete', key='name', middlewares=['auth|roles=admin'])
        ]
