from flasque.models import Role
from flasque.services import BaseService


class RoleService(BaseService):
    def __init__(self):
        super().__init__(Role)

    def get_by_name(self, name):
        return self.get_by('name', name)


role_service = RoleService()
