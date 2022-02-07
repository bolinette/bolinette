from bolinette.web import ext, Controller


@ext.controller("role", "/role")
class RoleController(Controller):
    def default_routes(self):
        return [
            self.defaults.get_all(middlewares=["auth|roles=admin"]),
            self.defaults.get_one(
                "complete", key="name", middlewares=["auth|roles=admin"]
            ),
        ]
