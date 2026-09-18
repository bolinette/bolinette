from collections.abc import Callable, Sequence
from typing import Any

from escondite import Cache
from soupape import AsyncInjector, ServiceCollection, post_init

from bolinette.core._extension import CoreExtension
from bolinette.core._startup import get_startup_functions
from bolinette.core.commands import CommandRunner
from bolinette.core.events import (
    BLNT_ERROR_EVENT,
    BLNT_INITIALIZED_EVENT,
    BLNT_STARTED_EVENT,
    BLNT_STOPPED_EVENT,
    EventContext,
    EventDispatcher,
    EventListener,
)
from bolinette.core.extensions import Extension, LoadedExtensions, resolve_extensions


class Bolinette:
    def __init__(
        self,
        cache: Cache,
        injector: AsyncInjector,
        event_dispatcher: EventDispatcher,
        command_runner: CommandRunner,
        extensions: LoadedExtensions,
    ) -> None:
        self._cache = cache
        self._injector = injector
        self._event_dispatcher = event_dispatcher
        self._command_runner = command_runner
        self._extensions = extensions
        self._started = False

    @property
    def injector(self) -> AsyncInjector:
        return self._injector

    @property
    def extensions(self) -> LoadedExtensions:
        return self._extensions

    @property
    def started(self) -> bool:
        return self._started

    @post_init
    async def _initialize(self) -> None:
        await self._event_dispatcher.dispatch(BLNT_INITIALIZED_EVENT)

    async def startup(self) -> None:
        if self._started:
            return
        try:
            async with self._injector.get_scoped_injector() as scoped_injector:
                for func in get_startup_functions(self._cache):
                    await scoped_injector.call(func)
        except Exception as err:
            await self._dispatch_error(err)
            raise
        self._started = True
        await self._event_dispatcher.dispatch(BLNT_STARTED_EVENT)

    def add_event_listener(self, event: str, listener: EventListener, priority: int = 1000) -> None:
        self._event_dispatcher.add_listener(event, listener, priority)

    async def dispatch_event(
        self,
        event: str,
        /,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
        *,
        context: EventContext[Any] | None = None,
    ) -> None:
        await self._event_dispatcher.dispatch(event, args=args, kwargs=kwargs, context=context)

    async def run_command(self, args: list[str]) -> int | None:
        try:
            cmd = self._command_runner.parse(args)
        except Exception as err:
            await self._dispatch_error(err)
            raise
        if cmd.run_startup:
            await self.startup()
        try:
            return await self._command_runner.run(cmd)
        except Exception as err:
            await self._dispatch_error(err)
            raise

    async def _dispatch_error(self, err: Exception) -> None:
        await self._event_dispatcher.dispatch(BLNT_ERROR_EVENT, context=EventContext(err))

    async def dispose(self) -> None:
        if self._started:
            await self._event_dispatcher.dispatch(BLNT_STOPPED_EVENT)
        await self._injector.__aexit__(None, None, None)


def _make_instance_resolver[T](interface: type[T], instance: T) -> Callable[[], T]:
    def _resolve() -> T:
        return instance

    _resolve.__annotations__ = {"return": interface}
    return _resolve


def register_extensions(
    extensions: Sequence[Extension],
    services: ServiceCollection,
    cache: Cache,
) -> list[Extension]:
    loaded = resolve_extensions(extensions, implicit=[CoreExtension])
    for ext in loaded:
        ext.register_services(services, cache)
        services.add_singleton(type(ext), _make_instance_resolver(type(ext), ext))
    services.add_from_cache(cache)
    return loaded


async def make_bolinette(
    extensions: Sequence[Extension] | None = None,
    *,
    cache: Cache | None = None,
    services: ServiceCollection | None = None,
) -> Bolinette:
    services = services if services is not None else ServiceCollection()
    app_cache = Cache() | Cache.with_fallback(cache)
    loaded = register_extensions(() if extensions is None else extensions, services, app_cache)
    services.add_singleton(LoadedExtensions, _make_instance_resolver(LoadedExtensions, LoadedExtensions(loaded)))
    injector = AsyncInjector(services)
    await injector.__aenter__()
    return await injector.require(Bolinette)
