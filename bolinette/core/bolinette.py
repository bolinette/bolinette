from typing import Callable

from bolinette.core import (
    Cache,
    Environment,
    Injection,
    InjectionStrategy,
    __core_cache__,
)
from bolinette.core.inject import InjectionContext
from bolinette.core.utils import paths


class Bolinette:
    def __init__(
        self, *, inject: Injection | None = None, cache: Cache | None = None
    ) -> None:
        self.paths = paths.PathHelper(paths.dirname(__file__))
        self._cache = cache or __core_cache__
        self._inject = inject or Injection(self._cache, InjectionContext())
        self._add_type_to_inject()
        self._env = self._inject.require(Environment)

    def _add_type_to_inject(self):
        self._inject.add(Bolinette, InjectionStrategy.Singleton, instance=self)
        self._inject.add(Environment, InjectionStrategy.Singleton)

    async def startup(self) -> None:
        for func in self._cache.init_funcs:
            await self._inject.call(func.function)


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
