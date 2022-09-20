from typing import Callable

from bolinette.core import (
    Cache,
    Environment,
    Injection,
    Logger,
    __core_cache__,
    meta,
    require,
)
from bolinette.core.command import Parser
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
        meta.set(self, self._inject)

        self._inject.add(Logger, "transcient")
        self._inject.add(PathUtils, "singleton", args=[PathUtils.dirname(__file__)])
        self._inject.add(FileUtils, "singleton")

        self._logger = self._inject.require(Logger[Bolinette])
        self._paths = self._inject.require(PathUtils)
        self._files = self._inject.require(FileUtils)

        self._profile = (
            profile
            or self._files.read_profile(self._paths.env_path())
            or self._set_default_profile()
        )

        self._inject.add(Bolinette, "singleton", instance=self)
        self._inject.add(
            Environment,
            "singleton",
            args=[self._profile],
            instanciate=True,
        )
        self._inject.add(Parser, "singleton")

    @property
    def injection(self) -> Injection:
        return self._inject

    def _set_default_profile(self) -> str:
        self._logger.warning(
            "No profile set, defaulting to 'development'.",
            "Be sure to set the current profile in a .profile file in the env folder",
        )
        return "development"

    async def startup(self) -> None:
        pass

    @require(Parser)
    def _parser(self):
        pass

    async def exec_cmd_args(self):
        await self._parser.run()


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
