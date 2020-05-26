from bolinette import blnt
from bolinette.decorators import service


@service('role')
class RoleService(blnt.Service):
    async def get_by_name(self, name):
        return await self.get_first_by('name', name)
