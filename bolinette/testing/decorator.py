from functools import wraps
from collections.abc import Callable, Awaitable
from typing import Any

from bolinette.testing import BolitestClient
from bolinette.utils.functions import async_invoke


def bolitest(*, before: Callable[[Any], Awaitable[None]] = None,
             after: Callable[[Any], Awaitable[None]] = None):
    def wrapper(func):
        @wraps(func)
        async def inner(client: BolitestClient):
            try:
                async with client:
                    await client.context.db.close_transaction()
                    await client.context.db.drop_all()
                    await client.context.db.create_all()
                    if before is not None:
                        await async_invoke(before, context=client.context, mock=client.mock)
                    await client.context.db.close_transaction()
                    await func(client=client)
                    if after is not None:
                        await async_invoke(after, context=client.context, mock=client.mock)
                    await client.context.db.close_transaction()
                    await client.context.db.drop_all()
            except Exception as e:
                await client.context.db.rollback_transaction()
                await client.context.db.drop_all()
                raise e
        return inner
    return wrapper
