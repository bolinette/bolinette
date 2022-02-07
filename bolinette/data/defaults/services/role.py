from bolinette.data import ext, Service
from bolinette.data.defaults.entities import Role


@ext.service("role")
class RoleService(Service[Role]):
    async def get_by_name(self, name, *, safe=False):
        return await self.get_first_by("name", name, safe=safe)
