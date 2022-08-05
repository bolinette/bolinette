from typing import Callable

from bolinette.core import (
    Cache,
    Environment,
    Injection,
    InjectionStrategy,
    Logger,
    __core_cache__,
)
from bolinette.core.inject import InjectionContext
from bolinette.core.utils import FileUtils, PathUtils


class Bolinette:
    def __init__(
        self,
        *,
        profile: str | None = None,
        inject: Injection | None = None,
        cache: Cache | None = None
    ) -> None:
        self._cache = cache or __core_cache__
        self._inject = inject or Injection(self._cache, InjectionContext())
        self._logger = self._inject.require(Logger[Bolinette])
        self._paths = PathUtils(PathUtils.dirname(__file__))
        self._files = FileUtils(self._paths)
        self._profile = (
            profile
            or self._files.read_profile(self._paths.env_path())
            or self._set_default_profile()
        )
        self._add_types_to_inject()

    @property
    def injection(self) -> Injection:
        return self._inject

    def _set_default_profile(self) -> str:
        self._logger.warning(
            "No profile set, defaulting to 'development'.",
            "Be sure to set the current profile in a .profile file in the env folder",
        )
        return "development"

    def _add_types_to_inject(self) -> None:
        self._inject.add(Bolinette, InjectionStrategy.Singleton, instance=self)
        self._inject.add(PathUtils, InjectionStrategy.Singleton, instance=self._paths)
        self._inject.add(FileUtils, InjectionStrategy.Singleton, instance=self._files)
        self._inject.add(Environment, InjectionStrategy.Singleton, args=[self._profile])
        self._inject.require(Environment)

    async def startup(self) -> None:
        for func in self._cache.init_funcs:
            await self._inject.call(func.function)


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
