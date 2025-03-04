import asyncio
import sys
from collections.abc import Callable
from typing import Any, NoReturn, Self

from bolinette import core
from bolinette.core import __user_cache__, meta
from bolinette.core.cache import Cache
from bolinette.core.command import Parser
from bolinette.core.environment import Environment
from bolinette.core.events import EventDispatcher
from bolinette.core.exceptions import InitError
from bolinette.core.extension import Extension, ExtensionModule, sort_extensions
from bolinette.core.injection import Injection, require
from bolinette.core.logging import Logger
from bolinette.core.startup import STARTUP_CACHE_KEY
from bolinette.core.types.type import Type


class Bolinette:
    def __init__(self, *, cache: Cache | None = None) -> None:
        self._cache = cache or Cache()
        self._initialized = False
        self._extensions: list[Extension] = [core.__blnt_ext__(self._cache)]
        self._inject: Injection
        self._env: Environment
        self.logger: Logger[Bolinette]

    def use_extension[ExtT: Extension](self, module: ExtensionModule[ExtT]) -> ExtT:
        if self._initialized:
            raise InitError("Cannot use extension after Bolinette startup")
        ext_type = module.__blnt_ext__
        ext = ext_type(self._cache)
        if ext in self._extensions:
            raise InitError(f"Bolinette extension {ext.name} is already in use")
        new_extentions: list[Extension] = [ext]
        for dep_module in ext.dependencies:
            ext_type = dep_module.__blnt_ext__
            dep_ext = next((e for e in self._extensions if isinstance(e, ext_type)), None)
            if dep_ext is None:
                dep_ext = ext_type(self._cache)
                new_extentions.append(dep_ext)
        self._extensions = sort_extensions([*self._extensions, *new_extentions])
        return ext

    @require(Parser)
    def _parser(self): ...

    @require(EventDispatcher)
    def _events(self): ...

    async def dispatch_event(self, event: str) -> None:
        await self._events.dispatch(event, self._inject.call)

    async def startup(self) -> Self:
        funcs: list[Callable[..., Any]] = self._cache.get(STARTUP_CACHE_KEY, raises=False)
        async with self._inject.get_async_scoped_session() as scoped_inject:
            for func in funcs:
                if asyncio.iscoroutine(res := scoped_inject.call(func)):
                    await res
        await self._events.dispatch("started", self._inject.call)
        return self

    def build(self) -> Self:
        if self._initialized:
            raise InitError("Bolinette has already been initialized")

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
