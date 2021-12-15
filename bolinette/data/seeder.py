from collections.abc import Callable
from bolinette import abc


class Seeder:
    def __init__(self, func: Callable[[abc.Context], None]) -> None:
        self._func = func
        self._name = func.__name__

    @property
    def name(self) -> str:
        return self._name

    async def run(self, context: abc.Context):
        return await self._func(context)
