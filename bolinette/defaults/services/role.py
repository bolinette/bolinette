from bolinette import core
from bolinette.decorators import service


@service('role')
class RoleService(core.Service):
    async def get_by_name(self, name):
        return await self.get_first_by('name', name)
