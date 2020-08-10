from bolinette import blnt, bcrypt
from bolinette.decorators import service
from bolinette.defaults.services import FileService
from bolinette.exceptions import ForbiddenError, BadRequestError


@service('user')
class UserService(blnt.Service):
    @staticmethod
    def encrypt_password(password):
        return bcrypt.hash_password(password)

    @staticmethod
    def check_password(user, password):
        return bcrypt.check_password(user.password, password)

    async def _check_params(self, values: dict):
        if values.get('password'):
            values['password'] = UserService.encrypt_password(values['password'])

    async def get_by_username(self, username, *, safe=False):
        return await self.get_first_by('username', username, safe=safe)

    async def get_by_email(self, email, *, safe=False):
        return await self.get_first_by('email', email, safe=safe)

    async def create(self, values: dict):
        await self._check_params(values)
        return await super().create(values)

    async def update(self, entity, values: dict):
        await self._check_params(values)
        return await super().update(entity, values)

    async def patch(self, entity, values: dict):
        await self._check_params(values)
        return await super().patch(entity, values)

    async def has_role(self, user, role_name):
        return any(filter(lambda r: r.name == role_name, user.roles))

    async def add_role(self, user, role):
        if role.name == 'root':
            raise ForbiddenError('role.root.forbidden')
        if role in user.roles:
            raise BadRequestError(f'user.roles.exists:{user.username}:{role.name}')
        user.roles.append(role)

    async def remove_role(self, current_user, user, role):
        if role.name == 'root':
            raise ForbiddenError('role.root.forbidden')
        if (current_user.username == user.username
                and role.name == 'admin'
                and not await self.has_role(current_user, 'root')):
            raise ForbiddenError('role.admin.no_self_demotion')
        if role not in user.roles:
            raise BadRequestError(f'user.roles.not_found:{user.username}:{role.name}')
        user.roles.remove(role)

    async def save_profile_picture(self, user, request_file):
        file_service: FileService = self.context.service('file')
        old_picture = user.profile_picture
        user.profile_picture = await file_service.save_file(request_file)
        if old_picture:
            await file_service.delete(old_picture)
        return user
