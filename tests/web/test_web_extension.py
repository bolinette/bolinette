from collections.abc import Awaitable, Callable
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest
from escondite import Cache
from soupape import ServiceCollection

from bolinette.core import CoreExtension, make_bolinette
from bolinette.core.commands.exceptions import CommandHelpError
from bolinette.core.exceptions import InitError
from bolinette.web import (
    AsgiApplication,
    BlntAuthOptions,
    Controller,
    WebExtension,
    controller,
    get,
    with_middleware,
)
from bolinette.web._config import BlntAuthOptions as ConfigOptions
from bolinette.web._resources import WebResources
from bolinette.web._scaffold import create_controllers_package, create_server_file
from bolinette.web.auth import Authenticated, AuthProviders, BolinetteAuthProvider, blnt_auth_user_transformer
from bolinette.web.ws import WebSocketContext, WebSocketSubResult, WebSocketSubscription, topic
from bolinette.web.ws._handler import WebSocketHandler
from tests.web.conftest import AppFactory, blnt_auth_env


class Tracer:
    def options(self) -> None:
        pass

    async def handle(self, next: Callable[[], Awaitable[Any]]) -> Any:
        return await next()


class UserInfo:
    def __init__(self, name: str) -> None:
        self.name = name


class TestExtensionShape:
    def test_name_and_dependencies(self) -> None:
        extension = WebExtension()

        assert extension.name == "web"
        assert list(extension.dependencies) == [CoreExtension]

    def test_options_default_to_none(self) -> None:
        assert BlntAuthOptions is ConfigOptions
        assert BlntAuthOptions() == BlntAuthOptions("auth", "")

    async def test_core_is_loaded_first(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        assert [type(ext) for ext in blnt.extensions] == [CoreExtension, WebExtension]

    def test_entry_point_is_advertised(self) -> None:
        entries = {e.name: e.value for e in metadata.entry_points(group="bolinette.extensions")}

        assert entries["web"] == "bolinette.web:WebExtension"

    def test_new_project_hooks(self) -> None:
        assert list(WebExtension().get_new_project_hooks()) == [create_server_file, create_controllers_package]


class TestServiceRegistration:
    async def test_singletons(self, make_app: AppFactory) -> None:
        services = ServiceCollection()

        await make_app(services=services)

        for service in (WebResources, AsgiApplication, WebSocketHandler, WebSocketContext, AuthProviders):
            assert services.is_registered(service)

    async def test_authenticated_is_scoped(self, make_app: AppFactory) -> None:
        services = ServiceCollection()

        await make_app(services=services)

        assert services.is_registered(Authenticated)

    async def test_controllers_middlewares_and_topics_are_registered(self, make_app: AppFactory, cache: Cache) -> None:
        @with_middleware(Tracer)
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                return "ok"

        @topic("rooms", cache=cache)
        class Rooms:
            async def subscribe(self, sub: WebSocketSubscription) -> WebSocketSubResult:
                return sub.accept()

        services = ServiceCollection()
        await make_app(services=services)

        assert services.is_registered(Ctrl)
        assert services.is_registered(Tracer)
        assert services.is_registered(Rooms)

    async def test_a_middleware_used_twice_is_registered_once(self, make_app: AppFactory, cache: Cache) -> None:
        @with_middleware(Tracer)
        @controller("a", cache=cache)
        class First(Controller):
            @get("")
            async def index(self) -> str:
                return "a"

        @with_middleware(Tracer)
        @controller("b", cache=cache)
        class Second(Controller):
            @get("")
            async def index(self) -> str:
                return "b"

        blnt = await make_app()

        assert blnt is not None

    @pytest.mark.parametrize("command", [["auth", "new", "rsa"], ["auth", "new", "encrypt"]])
    async def test_commands_are_registered(self, make_app: AppFactory, command: list[str]) -> None:
        blnt = await make_app()

        with pytest.raises(CommandHelpError) as raised:
            await blnt.run_command([*command, "--help"])

        assert " ".join(command) in raised.value.message


class TestBlntAuthWiring:
    async def test_nothing_auth_related_without_options(self, make_app: AppFactory) -> None:
        services = ServiceCollection()

        await make_app(services=services)

        assert not services.is_registered(BolinetteAuthProvider)

    async def test_options_register_the_provider(self, cache: Cache, env_folder: Path) -> None:
        blnt_auth_env(env_folder, 'type = "HS256"\nkey = "0123456789abcdef0123456789abcdef"')
        _transformer(cache)
        services = ServiceCollection()

        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache, services=services)
        await blnt.startup()

        assert services.is_registered(BolinetteAuthProvider)
        assert isinstance(await blnt.injector.require(BolinetteAuthProvider), BolinetteAuthProvider)
        await blnt.dispose()

    async def test_a_missing_section_fails_at_startup(self, cache: Cache, env_folder: Path) -> None:
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="blntauth"):
            await blnt.startup()

        await blnt.dispose()

    async def test_an_invalid_section_fails_at_startup(self, cache: Cache, env_folder: Path) -> None:
        (env_folder / "env.toml").write_text('[blntauth]\nissuer = "x"\n')
        _transformer(cache)
        blnt = await make_bolinette([WebExtension(blnt_auth=BlntAuthOptions())], cache=cache)

        with pytest.raises(InitError, match="invalid 'blntauth'"):
            await blnt.startup()

        await blnt.dispose()


def _transformer(cache: Cache) -> type[Any]:
    @blnt_auth_user_transformer(cache=cache)
    class Transformer:
        def check_user(self, payload: dict[str, Any], /) -> UserInfo:
            return UserInfo(str(payload.get("name")))

        def user_from_claims(self, claims: dict[str, Any], /) -> UserInfo:
            return UserInfo(claims["name"])

        def user_to_claims(self, user_info: UserInfo, /) -> dict[str, Any]:
            return {"name": user_info.name}

    return Transformer


class TestDeduplication:
    async def test_a_class_registered_twice_is_only_added_once(self, make_app: AppFactory, cache: Cache) -> None:
        from bolinette.web.auth import auth_provider

        @auth_provider(cache=cache)
        @controller("dual", cache=cache)
        class Dual(Controller):
            issuer = "dual"

            @get("")
            async def index(self) -> str:
                return "dual"

            def validate(self, token: str) -> dict[str, Any]:
                return {}

        blnt = await make_app()

        assert isinstance(await blnt.injector.require(Dual), Dual)
