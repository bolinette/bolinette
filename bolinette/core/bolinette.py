import asyncio
import sys
from collections.abc import Callable
from typing import Any, NoReturn, Self

from bolinette import core
from bolinette.core import __user_cache__, meta
from bolinette.core.cache import Cache
from bolinette.core.command import Parser
from bolinette.core.environment import Environment
from bolinette.core.exceptions import InitError
from bolinette.core.extension import Extension, ExtensionModule
from bolinette.core.injection import Injection, require
from bolinette.core.logging import Logger
from bolinette.core.startup import STARTUP_CACHE_KEY
from bolinette.core.types.type import Type


class Bolinette:
    def __init__(self) -> None:
        self._cache = Cache()
        self._initialized = False
        self._extensions: list[Extension] = [core.__blnt_ext__]
        self._inject: Injection
        self._env: Environment
        self.logger: Logger[Bolinette]

    def use_extension[ExtT: Extension](self, ext: ExtensionModule[ExtT] | ExtT) -> ExtT:
        if self._initialized:
            raise InitError("Cannot use extension after Bolinette startup")
        if not isinstance(ext, Extension):
            ext = ext.__blnt_ext__
        if ext in self._extensions:
            raise InitError(f"Bolinette extension {ext.name} is already in use")
        self._extensions.append(ext)
        for dep_ext in ext.dependencies:
            if dep_ext not in self._extensions:
                self._extensions.append(dep_ext)
        return ext

    @require(Parser)
    def _parser(self): ...

    async def startup(self) -> Self:
        funcs: list[Callable[..., Any]] = self._cache.get(STARTUP_CACHE_KEY, raises=False)
        async with self._inject.get_async_scoped_session() as scoped_inject:
            for func in funcs:
                if asyncio.iscoroutine(res := scoped_inject.call(func)):
                    await res
        return self

    def build(self) -> Self:
        if self._initialized:
            raise InitError("Bolinette has already been initialized")
        self._extensions = Extension.sort_extensions(self._extensions)
        for ext in self._extensions:
            ext.add_cached(self._cache)

        self._cache |= __user_cache__

        self._inject = Injection(self._cache)
        meta.set(self, self._inject)
        self._env = self._inject.require(Environment)
        self._cache.debug = self._env.config.get("core", {}).get("debug", False)

        self._inject.add_singleton(Bolinette, instance=self)
        self._inject.__hook_proxies__(Type(Bolinette), "singleton", self)

        self.logger = self._inject.require(Logger[Bolinette])
        self.logger.info(f"Loaded Bolinette with extensions: {', '.join(e.name for e in self._extensions)}")
        self._initialized = True

        return self

    @property
    def injection(self) -> Injection:
        return self._inject

    async def exec_args(self, args: list[str]) -> NoReturn:
        if not self._initialized:
            self.build()
        cmd, cmd_args = self._parser.parse_command(args)
        if cmd.run_startup:
            await self.startup()
        result = await self._inject.call(cmd.func, named_args=cmd_args)
        sys.exit(result or 0)
