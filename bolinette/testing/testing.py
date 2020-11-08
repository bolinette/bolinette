from functools import wraps
from typing import Callable, Awaitable

import pytest

from bolinette import Bolinette, blnt
from bolinette.testing import TestClient, Mock


@pytest.fixture
def client(loop, aiohttp_client):
    bolinette = Bolinette(profile='test',
                          overrides={'DBMS': 'SQLITE', 'SECRET_KEY': 'super secret'})
    client = loop.run_until_complete(aiohttp_client(bolinette.app))
    return TestClient(client, bolinette.context)


def bolitest(*, before: Callable[[blnt.BolinetteContext, Mock], Awaitable[None]] = None,
             after: Callable[[blnt.BolinetteContext, Mock], Awaitable[None]] = None):
    def wrapper(func):
        @wraps(func)
        async def inner(client: TestClient):
            await client.context.db.drop_all()
            await client.context.db.create_all()
            if before is not None:
                await before(client.context, client.mock)
            client.context.db.session.commit()
            await func(client=client)
            if after is not None:
                await after(client.context, client.mock)
            await client.context.db.drop_all()
        return inner
    return wrapper
