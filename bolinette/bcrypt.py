import bcrypt as py_bcrypt


class Bcrypt:
    def hash_password(self, password):
        return py_bcrypt.hashpw(password.encode(), py_bcrypt.gensalt())

    def check_password(self, hashed, password):
        return py_bcrypt.checkpw(password.encode(), hashed)


bcrypt = Bcrypt()
