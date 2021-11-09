import bcrypt

from bolinette import abc, core
from bolinette.decorators import service
from bolinette.exceptions import ForbiddenError, UnprocessableEntityError
from bolinette.defaults.services import FileService


@service('user')
class UserService(core.Service):
    def __init__(self, context: abc.Context, file_service: FileService):
        super().__init__(context)
        self.file_service = file_service

    @staticmethod
    def encrypt_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def check_password(user, password):
        return bcrypt.checkpw(password.encode(), user.password.encode())

    @staticmethod
    async def _check_params(values: dict):
        if values.get('password'):
            values['password'] = UserService.encrypt_password(values['password'])

    async def get_by_username(self, username, *, safe=False):
        return await self.get_first_by('username', username, safe=safe)

    async def get_by_email(self, email, *, safe=False):
        return await self.get_first_by('email', email, safe=safe)

    async def create(self, values: dict, **kwargs):
        await self._check_params(values)
        return await super().create(values)

    async def update(self, entity, values: dict, **kwargs):
        await self._check_params(values)
        return await super().update(entity, values)

    async def patch(self, entity, values: dict, **kwargs):
        await self._check_params(values)
        return await super().patch(entity, values)

    @staticmethod
    async def has_role(user, role_name):
        return any(filter(lambda r: r.name == role_name, user.roles))

    @staticmethod
    async def add_role(user, role):
        if role.name == 'root':
            raise ForbiddenError('role.root.forbidden')
        if role in user.roles:
            raise UnprocessableEntityError(f'user.roles.exists:{user.username}:{role.name}')
        user.roles.append(role)

    async def remove_role(self, current_user, user, role):
        if role.name == 'root':
            raise ForbiddenError('role.root.forbidden')
        if (current_user.username == user.username
                and role.name == 'admin'
                and not await self.has_role(current_user, 'root')):
            raise ForbiddenError('role.admin.no_self_demotion')
        if role not in user.roles:
            raise UnprocessableEntityError(f'user.roles.not_found:{user.username}:{role.name}')
        user.roles.remove(role)

    async def save_profile_picture(self, user, request_file):
        old_picture = user.profile_picture
        user.profile_picture = await self.file_service.save_file(request_file)
        if old_picture:
            await self.file_service.delete(old_picture)
        return user
