import bcrypt as py_bcrypt

from bolinette import env


class Bcrypt:
    def __init__(self):
        self.secret_key = None

    def init_app(self):
        self.secret_key = env['SECRET_KEY']

    def hash_password(self, password):
        return py_bcrypt.hashpw(password.encode(), py_bcrypt.gensalt())

    def check_password(self, hashed, password):
        return py_bcrypt.checkpw(password.encode(), hashed)


bcrypt = Bcrypt()
