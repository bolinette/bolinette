from bolinette.data import ext, Service


@ext.service('role')
class RoleService(Service):
    async def get_by_name(self, name, *, safe=False):
        return await self.get_first_by('name', name, safe=safe)
