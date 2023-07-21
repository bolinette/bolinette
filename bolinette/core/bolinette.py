from typing import Callable, Protocol

from bolinette.core import (
    Environment,
    Extension,
    Logger,
    __user_cache__,
    core_ext,
    meta,
)
from bolinette.core.command import Parser
from bolinette.core.injection import Injection
from bolinette.core.utils import FileUtils, PathUtils


class _ExtensionModule(Protocol):
    __blnt_ext__: Extension


class Bolinette:
    def __init__(
        self,
        *,
        profile: str | None = None,
        inject: Injection | None = None,
        load_defaults: bool = True,
        extensions: list[_ExtensionModule] | None = None,
    ) -> None:
        if extensions is None:
            _extensions = []
        else:
            _extensions = [m.__blnt_ext__ for m in extensions]
        if load_defaults and core_ext not in _extensions:
            _extensions = [core_ext, *_extensions]

        _extensions = Extension.sort_extensions(_extensions)
        cache = Extension.merge_caches(_extensions)
        cache |= __user_cache__

        self._inject = inject or Injection(cache)
        meta.set(self, self._inject)

        self._logger = self._inject.require(Logger[Bolinette])
        self._paths = self._inject.require(PathUtils)
        self._files = self._inject.require(FileUtils)

        self._profile = profile or self._files.read_profile(self._paths.env_path()) or self._set_default_profile()

        self._inject.add(Bolinette, "singleton", instance=self)
        self._inject.add(
            Environment,
            "singleton",
            args=[self._profile],
            instanciate=True,
        )
        self._inject.__hook_proxies__(self)

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

    @property
    def _parser(self) -> Parser:
        ...

    async def exec_cmd_args(self):
        await self._parser.run()


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
