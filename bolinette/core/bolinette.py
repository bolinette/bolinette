import importlib
import pkgutil
import sys
from collections.abc import Callable
from types import ModuleType
from typing import NoReturn

import bolinette
from bolinette.core import Extension, Logger, __user_cache__, meta
from bolinette.core.cache import Cache
from bolinette.core.command import Parser
from bolinette.core.environment import Environment
from bolinette.core.exceptions import InitError
from bolinette.core.injection import Injection, require


class Bolinette:
    def __init__(
        self,
        *,
        profile: str | None = None,
    ) -> None:
        self.cache = Cache()

        self.extensions = self._load_extensions()
        for ext in self.extensions:
            ext.add_cached(self.cache)

        self.cache |= __user_cache__

        self._inject = Injection(self.cache)
        meta.set(self, self._inject)
        self._env = self._inject.require(Environment)
        self.cache.debug = self._env.config["core"]["debug"]

        self._inject.add(Bolinette, "singleton", instance=self)
        self._inject.__hook_proxies__(self)

        self._logger = self._inject.require(Logger[Bolinette])
        self._logger.info(f"Loaded Bolinette with extensions: {', '.join(e.name for e in self.extensions)}")

    @property
    def injection(self) -> Injection:
        return self._inject

    def _load_extensions(self) -> list[Extension]:
        def iter_namespace(module: ModuleType) -> list[str]:
            return [info[1] for info in pkgutil.iter_modules(module.__path__, module.__name__ + ".")]

        blnt_modules = [importlib.import_module(name) for name in iter_namespace(bolinette)]
        extensions: list[Extension] = []
        for module in blnt_modules:
            if not hasattr(module, "__blnt_ext__") or not isinstance(ext := module.__blnt_ext__, Extension):
                raise InitError(f"{module.__name__} is not a valid Bolinette extension module")
            extensions.append(ext)
        return Extension.sort_extensions(extensions)

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
        ...

    async def run_from_args(self) -> NoReturn:
        cmd, args = self._parser.parse_command()
        result = await self._inject.call(cmd, named_args=args)
        sys.exit(result or 0)


def main_func(func: Callable[[], Bolinette]) -> Callable[[], Bolinette]:
    setattr(func, "__blnt__", "__blnt_main__")
    return func
