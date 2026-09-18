"""Application lifecycle: construction, startup, event dispatch and disposal."""

import pytest
from escondite import Cache
from soupape import AsyncInjector, ServiceCollection
from soupape.errors import CircularDependencyError

from bolinette.core import Bolinette, startup
from bolinette.core.commands import command
from bolinette.core.commands.exceptions import CommandUsageError
from bolinette.core.events import (
    BLNT_ERROR_EVENT,
    BLNT_INITIALIZED_EVENT,
    BLNT_STARTED_EVENT,
    BLNT_STOPPED_EVENT,
    EventContext,
    on_error,
    on_event,
    on_initialized,
    on_started,
    on_stopped,
)
from tests.core.conftest import AppFactory


class TestConstruction:
    async def test_make_bolinette_returns_an_app(self, make_app: AppFactory) -> None:
        """`make_bolinette` builds a `Bolinette` that is not started yet."""
        blnt = await make_app()

        assert isinstance(blnt, Bolinette)
        assert not blnt.started

    async def test_initialized_event_fires_on_construction(self, make_app: AppFactory, cache: Cache) -> None:
        """Listeners of the initialized event run before `make_bolinette` returns."""
        fired: list[str] = []

        @on_initialized(cache=cache)
        async def listener() -> None:
            fired.append("initialized")

        await make_app()

        assert fired == ["initialized"]

    async def test_app_is_injectable_once_built(self, make_app: AppFactory, cache: Cache) -> None:
        """The application instance can be injected into listeners that run after construction."""
        seen: list[Bolinette] = []

        @on_started(cache=cache)
        async def listener(blnt: Bolinette) -> None:
            seen.append(blnt)

        blnt = await make_app()
        await blnt.startup()

        assert seen == [blnt]

    async def test_app_cannot_be_injected_while_initializing(self, make_app: AppFactory, cache: Cache) -> None:
        """The initialized event fires during construction, so requiring the app there is a cycle."""

        @on_initialized(cache=cache)
        async def listener(blnt: Bolinette) -> None:
            pass

        with pytest.raises(CircularDependencyError):
            await make_app()

    async def test_user_cache_is_a_fallback(self, make_app: AppFactory, cache: Cache) -> None:
        """Decorators registered in the user cache are seen by the application."""
        fired: list[str] = []

        @on_initialized(cache=cache)
        async def listener() -> None:
            fired.append("user")

        await make_app()

        assert fired == ["user"]

    async def test_user_services_are_available(self, make_app: AppFactory) -> None:
        """Services added to the given collection are resolvable in the application."""

        class Service:
            pass

        services = ServiceCollection()
        services.add_singleton(Service)
        await make_app(services=services)

        assert services.is_registered(Bolinette)
        assert services.is_registered(Service)

    async def test_injector_is_exposed(self, make_app: AppFactory) -> None:
        """The application injector is available to open scopes from outside the framework."""
        blnt = await make_app()

        async with blnt.injector.get_scoped_injector() as scope:
            assert await scope.require(Bolinette) is blnt

    async def test_two_apps_do_not_share_state(self, make_app: AppFactory) -> None:
        """Building two applications from the same cache yields independent instances."""
        first = await make_app()
        second = await make_app()

        assert first is not second


class TestStartup:
    async def test_startup_runs_startup_functions(self, make_app: AppFactory, cache: Cache) -> None:
        """Functions decorated with `startup` run on `startup()`, not on construction."""
        calls: list[str] = []

        @startup(cache=cache)
        async def init() -> None:
            calls.append("init")

        blnt = await make_app()
        assert calls == []

        await blnt.startup()

        assert calls == ["init"]
        assert blnt.started

    async def test_startup_functions_are_injected(self, make_app: AppFactory, cache: Cache) -> None:
        """Startup functions receive their dependencies from a scoped injector."""
        seen: list[AsyncInjector] = []

        @startup(cache=cache)
        async def init(injector: AsyncInjector) -> None:
            seen.append(injector)

        blnt = await make_app()
        await blnt.startup()

        assert len(seen) == 1

    async def test_sync_startup_function(self, make_app: AppFactory, cache: Cache) -> None:
        """A plain function can be a startup function too."""
        calls: list[str] = []

        @startup(cache=cache)
        def init() -> None:
            calls.append("init")

        blnt = await make_app()
        await blnt.startup()

        assert calls == ["init"]

    async def test_startup_is_idempotent(self, make_app: AppFactory, cache: Cache) -> None:
        """Calling `startup()` twice runs startup functions and listeners once."""
        calls: list[str] = []

        @startup(cache=cache)
        async def init() -> None:
            calls.append("init")

        @on_started(cache=cache)
        async def started() -> None:
            calls.append("started")

        blnt = await make_app()
        await blnt.startup()
        await blnt.startup()

        assert calls == ["init", "started"]

    async def test_started_event_fires_after_startup_functions(self, make_app: AppFactory, cache: Cache) -> None:
        """The started event is dispatched once every startup function has run."""
        calls: list[str] = []

        @on_started(cache=cache)
        async def started() -> None:
            calls.append("started")

        @startup(cache=cache)
        async def init() -> None:
            calls.append("init")

        blnt = await make_app()
        await blnt.startup()

        assert calls == ["init", "started"]


class TestDispose:
    async def test_dispose_fires_stopped_when_started(self, make_app: AppFactory, cache: Cache) -> None:
        """Disposing a started application dispatches the stopped event."""
        calls: list[str] = []

        @on_stopped(cache=cache)
        async def stopped() -> None:
            calls.append("stopped")

        blnt = await make_app()
        await blnt.startup()
        await blnt.dispose()

        assert calls == ["stopped"]

    async def test_dispose_skips_stopped_when_not_started(self, make_app: AppFactory, cache: Cache) -> None:
        """An application that never started does not dispatch the stopped event."""
        calls: list[str] = []

        @on_stopped(cache=cache)
        async def stopped() -> None:
            calls.append("stopped")

        blnt = await make_app()
        await blnt.dispose()

        assert calls == []


class TestEvents:
    async def test_dispatch_event_reaches_decorated_listeners(self, make_app: AppFactory, cache: Cache) -> None:
        """A custom event dispatched by the application reaches listeners from the cache."""
        received: list[int] = []

        @on_event("custom", cache=cache)
        async def listener(value: int) -> None:
            received.append(value)

        blnt = await make_app()
        await blnt.dispatch_event("custom", args=[3])
        await blnt.dispatch_event("custom", kwargs={"value": 4})

        assert received == [3, 4]

    async def test_add_event_listener_at_runtime(self, make_app: AppFactory) -> None:
        """Listeners added after construction are called on dispatch."""
        calls: list[str] = []

        async def listener() -> None:
            calls.append("called")

        blnt = await make_app()
        blnt.add_event_listener("custom", listener)
        await blnt.dispatch_event("custom")

        assert calls == ["called"]

    async def test_runtime_listener_priority(self, make_app: AppFactory) -> None:
        """Runtime listeners are ordered by priority, lowest first."""
        calls: list[str] = []

        async def late() -> None:
            calls.append("late")

        async def early() -> None:
            calls.append("early")

        blnt = await make_app()
        blnt.add_event_listener("custom", late, priority=200)
        blnt.add_event_listener("custom", early, priority=100)
        await blnt.dispatch_event("custom")

        assert calls == ["early", "late"]

    def test_lifecycle_event_names(self) -> None:
        """Lifecycle event names are stable strings under the `blnt:life:` prefix."""
        assert BLNT_INITIALIZED_EVENT == "blnt:life:initialized"
        assert BLNT_STARTED_EVENT == "blnt:life:started"
        assert BLNT_STOPPED_EVENT == "blnt:life:stopped"
        assert BLNT_ERROR_EVENT == "blnt:life:error"


class TestErrors:
    async def test_command_failure_fires_error_event(self, make_app: AppFactory, cache: Cache) -> None:
        """An exception raised by a command is given to error listeners, then re-raised."""
        seen: list[BaseException] = []

        @on_error(cache=cache)
        async def listener(context: EventContext[Exception]) -> None:
            seen.append(context.value)

        @command("boom", "Fails", cache=cache)
        async def boom() -> None:
            raise RuntimeError("boom")

        blnt = await make_app()

        with pytest.raises(RuntimeError, match="boom") as info:
            await blnt.run_command(["boom"])

        assert seen == [info.value]

    async def test_startup_failure_fires_error_event(self, make_app: AppFactory, cache: Cache) -> None:
        """An exception in a startup function reaches error listeners, is re-raised, and the app stays unstarted."""
        seen: list[BaseException] = []

        @on_error(cache=cache)
        async def listener(context: EventContext[Exception]) -> None:
            seen.append(context.value)

        @startup(cache=cache)
        async def init() -> None:
            raise RuntimeError("init failed")

        blnt = await make_app()

        with pytest.raises(RuntimeError, match="init failed") as info:
            await blnt.startup()

        assert seen == [info.value]
        assert not blnt.started

    async def test_failed_startup_does_not_fire_stopped(self, make_app: AppFactory, cache: Cache) -> None:
        """An application whose startup failed is not started, so disposing it fires no stopped event."""
        calls: list[str] = []

        @startup(cache=cache)
        async def init() -> None:
            raise RuntimeError("init failed")

        @on_stopped(cache=cache)
        async def stopped() -> None:
            calls.append("stopped")

        blnt = await make_app()
        with pytest.raises(RuntimeError):
            await blnt.startup()
        await blnt.dispose()

        assert calls == []

    async def test_bad_invocation_fires_error_event(self, make_app: AppFactory, cache: Cache) -> None:
        """A command line the parser rejects is given to error listeners before being raised."""
        seen: list[BaseException] = []

        @on_error(cache=cache)
        async def listener(context: EventContext[Exception]) -> None:
            seen.append(context.value)

        blnt = await make_app()

        with pytest.raises(CommandUsageError) as info:
            await blnt.run_command(["nope"])

        assert seen == [info.value]

    async def test_system_exit_is_not_an_error(self, make_app: AppFactory, cache: Cache) -> None:
        """A command ending the process with `SystemExit` does not fire the error event."""
        calls: list[str] = []

        @on_error(cache=cache)
        async def listener() -> None:
            calls.append("error")

        @command("quit", "Quits", cache=cache)
        async def quit_command() -> None:
            raise SystemExit(3)

        blnt = await make_app()

        with pytest.raises(SystemExit):
            await blnt.run_command(["quit"])

        assert calls == []
