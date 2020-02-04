from bolinette import bcrypt
from bolinette.models import User
from bolinette.services import BaseService


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


user_service = UserService()
