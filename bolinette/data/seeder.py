from collections.abc import Callable
from bolinette import core, data


class Seeder:
    def __init__(self, func: Callable[[core.BolinetteContext], None]) -> None:
        self._func = func
        self._name = func.__name__

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: core.BolinetteContext, data_ctx: data.DataContext):
        return await self._func(context, data_ctx)
