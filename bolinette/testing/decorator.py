from functools import wraps
from collections.abc import Callable, Awaitable
from typing import Any

from bolinette.testing import BolitestClient
from bolinette.utils.functions import invoke


def bolitest(
    *,
    before: Callable[[Any], Awaitable[None]] = None,
    after: Callable[[Any], Awaitable[None]] = None
):
    def wrapper(func):
        @wraps(func)
        async def inner(client: BolitestClient):
            try:
                async with client:
                    await client.data_ctx.db.close_transaction()
                    await client.data_ctx.db.drop_all()
                    await client.data_ctx.db.create_all()
                    if before is not None:
                        await invoke(before, context=client.context, mock=client.mock)
                    await client.data_ctx.db.close_transaction()
                    await func(client=client)
                    if after is not None:
                        await invoke(after, context=client.context, mock=client.mock)
                    await client.data_ctx.db.close_transaction()
                    await client.data_ctx.db.drop_all()
            except Exception as e:
                await client.data_ctx.db.rollback_transaction()
                await client.data_ctx.db.drop_all()
                raise e

        return inner

    return wrapper
