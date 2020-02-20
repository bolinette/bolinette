from bolinette import bcrypt
from bolinette.models import User
from bolinette.services import BaseService
from bolinette.exceptions import ForbiddenError, BadRequestError


class UserService(BaseService):
    @staticmethod
    def encrypt_password(password):
        return bcrypt.generate_password_hash(password).decode('utf-8')

    def __init__(self):
        super().__init__(User, 'user')

    def get_by_username(self, username):
        return self.get_first_by('username', username)

    def get_by_email(self, email):
        return self.get_first_by('email', email)

    def check_password(self, user, password):
        return bcrypt.check_password_hash(user.password, password)

    def create(self, params):
        params['password'] = UserService.encrypt_password(params['password'])
        return super().create(params)

    def update(self, entity, params):
        if 'password' in params:
            params['password'] = UserService.encrypt_password(params['password'])
        return super().update(entity, params)

    def patch(self, entity, params):
        if 'password' in params:
            params['password'] = UserService.encrypt_password(params['password'])
        return super().patch(entity, params)

    def add_role(self, user, role):
        if role.name == 'root':
            raise ForbiddenError('role.root.forbidden')
        if role in user.roles:
            raise BadRequestError(f'user.roles.exists:{user.username}:{role.name}')
        user.roles.append(role)

    def remove_role(self, current_user, user, role):
        if role.name == 'root':
            raise ForbiddenError('role.root.forbidden')
        if (current_user.username == user.username
                and role.name == 'admin'
                and not current_user.has_role('root')):
            raise ForbiddenError('role.admin.no_self_demotion')
        if role not in user.roles:
            raise BadRequestError(f'user.roles.not_found:{user.username}:{role.name}')
        user.roles.remove(role)


user_service = UserService()
