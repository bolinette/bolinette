import bcrypt as py_bcrypt


class Bcrypt:
    def hash_password(self, password: str):
        return py_bcrypt.hashpw(password.encode(), py_bcrypt.gensalt()).decode()

    def check_password(self, hashed: str, password: str):
        return py_bcrypt.checkpw(password.encode(), hashed.encode())


bcrypt = Bcrypt()
