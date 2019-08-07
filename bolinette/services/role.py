from bolinette.models import Role
from bolinette.services import BaseService


class RoleService(BaseService):
    def __init__(self):
        super().__init__(Role, 'role')

    def get_by_name(self, name):
        return self.get_first_by('name', name)


role_service = RoleService()
