from bolinette.models import Role
from bolinette.services import BaseService


class RoleService(BaseService):
    def __init__(self):
        super().__init__(Role)

    def get_by_name(self, name):
        return self.get_by('name', name)


role_service = RoleService()
