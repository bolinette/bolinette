from bolinette import bcrypt
from bolinette.testing import Mocked


def salt_password(mocked: Mocked) -> Mocked:
    mocked['password'] = bcrypt.hash_password(mocked['password'])
    return mocked
