import inspect
from functools import wraps
from typing import Callable, Awaitable, Any

from bolinette import blnt
from bolinette.testing import TestClient, Bolitest
from bolinette.utils.functions import async_invoke


def bolitest(*, before: Callable[[Any], Awaitable[None]] = None,
             after: Callable[[Any], Awaitable[None]] = None):
    def wrapper(func):
        @wraps(func)
        async def inner(client: TestClient):
            await client.context.db.drop_all()
            await client.context.db.create_all()
            if before is not None:
                await async_invoke(before, context=client.context, mock=client.mock)
            await client.context.db.close_transaction()
            await func(client=client)
            if after is not None:
                await async_invoke(after, context=client.context, mock=client.mock)
            await client.context.db.drop_all()
        blnt.cache.test_funcs.append(Bolitest(inner, inspect.getfile(func)))
        return inner
    return wrapper
