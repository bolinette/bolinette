from bolinette import bcrypt, services
from bolinette.exceptions import ForbiddenError, BadRequestError


class UserService(services.BaseService):
    @staticmethod
    def encrypt_password(password):
        return bcrypt.hash_password(password)

    def __init__(self):
        super().__init__('user')

    async def get_by_username(self, username):
        return await self.get_first_by('username', username)

    async def get_by_email(self, email):
        return await self.get_first_by('email', email)

    async def check_password(self, user, password):
        return bcrypt.check_password(user.password, password)

    async def _check_params(self, params: dict):
        if params.get('password'):
            params['password'] = UserService.encrypt_password(params['password'])
        if params.get('timezone') and not await services.get('tz').is_valid(params['timezone']):
            raise BadRequestError(f'timezone.invalid:{params["timezone"]}')

    async def create(self, params: dict, **_):
        await self._check_params(params)
        return await super().create(params)

    async def update(self, entity, params: dict, **_):
        await self._check_params(params)
        return await super().update(entity, params)

    async def patch(self, entity, params: dict, **_):
        await self._check_params(params)
        return await super().patch(entity, params)

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
                and not await user_service.has_role(current_user, 'root')):
            raise ForbiddenError('role.admin.no_self_demotion')
        if role not in user.roles:
            raise BadRequestError(f'user.roles.not_found:{user.username}:{role.name}')
        user.roles.remove(role)

    async def save_profile_picture(self, user, request_file):
        old_picture = user.profile_picture
        user.profile_picture = await services.get('file').save_file(request_file)
        if old_picture:
            await services.get('file').delete(old_picture)
        return user


user_service = UserService()
