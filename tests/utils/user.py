from bolinette import bcrypt
from bolinette.testing import Mocked


def salt_password(mocked: Mocked) -> Mocked:
    mocked.fields.password = bcrypt.hash_password(mocked.fields.password)
    return mocked
