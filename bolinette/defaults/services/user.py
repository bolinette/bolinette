from bolinette import data, bcrypt
from bolinette.decorators import service


@service('user')
class UserService(data.Service):
    @staticmethod
    def encrypt_password(password):
        return bcrypt.hash_password(password)

    @staticmethod
    def check_password(user, password):
        return bcrypt.check_password(user.password, password)

    async def _check_params(self, values: dict):
        if values.get('password'):
            values['password'] = UserService.encrypt_password(values['password'])

    async def get_by_username(self, username):
        return await self.get_first_by('username', username)

    async def get_by_email(self, email):
        return await self.get_first_by('email', email)

    async def create(self, values: dict, **_):
        await self._check_params(values)
        return await super().create(values)

    async def update(self, entity, values: dict, **_):
        await self._check_params(values)
        return await super().update(entity, values)

    async def patch(self, entity, values: dict, **_):
        await self._check_params(values)
        return await super().patch(entity, values)

    async def has_role(self, user, role_name):
        return any(filter(lambda r: r.name == role_name, user.roles))
