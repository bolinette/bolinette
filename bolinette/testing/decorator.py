from functools import wraps
from typing import Callable, Awaitable

from bolinette import blnt
from bolinette.testing import TestClient, Mock


def bolitest(*, before: Callable[['blnt.BolinetteContext', Mock], Awaitable[None]] = None,
             after: Callable[['blnt.BolinetteContext', Mock], Awaitable[None]] = None):
    def wrapper(func):
        @wraps(func)
        async def inner(client: TestClient):
            await client.context.db.drop_all()
            await client.context.db.create_all()
            if before is not None:
                await before(client.context, client.mock)
            await client.context.db.close_transaction()
            await func(client=client)
            if after is not None:
                await after(client.context, client.mock)
            await client.context.db.drop_all()
        blnt.cache.test_funcs.append(inner)
        return inner
    return wrapper
