from bolinette import bcrypt
from bolinette.models import User
from bolinette.services import BaseService


class UserService(BaseService):
    def __init__(self):
        super().__init__(User)

    def get_by_username(self, username):
        return self.get_by('username', username)

    def get_by_email(self, email):
        return self.get_by('email', email)

    def check_password(self, user, password):
        return bcrypt.check_password_hash(user.password, password)

    def create(self, **kwargs):
        kwargs['password'] = bcrypt.generate_password_hash(kwargs['password'])
        return super().create(**kwargs)


user_service = UserService()
