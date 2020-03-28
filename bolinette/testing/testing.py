from functools import wraps
import pytest

from bolinette import Bolinette, db
from bolinette.routing import web
from bolinette.testing import TestClient


@pytest.fixture
def client(loop, aiohttp_client):
    Bolinette(profile='test',
              overrides={'DBMS': 'SQLITE', 'SECRET_KEY': 'super secret'})
    client = loop.run_until_complete(aiohttp_client(web.app))
    return TestClient(client)


def bolitest(*, before=None, after=None):
    def wrapper(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            await db.engine.drop_all()
            await db.engine.create_all()
            if before is not None and callable(before):
                before()
            db.engine.session.commit()
            await func(*args, **kwargs)
            if after is not None and callable(after):
                after()
            await db.engine.drop_all()
        return inner
    return wrapper
