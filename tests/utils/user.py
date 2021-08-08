import bcrypt

from bolinette.testing import Mocked


def salt_password(mocked: Mocked) -> Mocked:
    mocked['password'] = bcrypt.hashpw(mocked['password'].encode(), bcrypt.gensalt()).decode()
    return mocked
