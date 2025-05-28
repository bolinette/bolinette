from typing import Self

from bolinette import core
from bolinette.core import Cache, startup
from bolinette.core.command import command
from bolinette.core.environment import environment
from bolinette.core.extension import Extension, ExtensionModule
from bolinette.core.injection import Injection, injectable
from bolinette.web.auth import AuthProviders, BlntAuthConfig, BolinetteAuthProvider
from bolinette.web.commands import new_encryption_key, new_rsa_key
from bolinette.web.commands.new_project import register_new_project_hooks
from bolinette.web.config import BlntAuthProps
from bolinette.web.resources import WebResources
from bolinette.web.ws import WebSocketHandler


class WebExtension:
    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self.name: str = "web"
        self.dependencies: list[ExtensionModule[Extension]] = [core]

        injectable(strategy="singleton", cache=cache)(WebResources)
        injectable(strategy="singleton", cache=cache)(WebSocketHandler)
        injectable(strategy="singleton", cache=cache)(AuthProviders)

        environment("blntauth", cache=cache)(BlntAuthConfig)

        command("auth new rsa", "Creates a new RSA key", cache=cache)(new_rsa_key)
        command("auth new encrypt", "Creates a new encryption key", cache=cache)(new_encryption_key)

        register_new_project_hooks(cache)

    def use_blnt_auth(self, ctrl_path: str = "auth", route_path: str = "") -> Self:
        async def init_blnt_auth(inject: Injection, providers: AuthProviders) -> None:
            inject.add_singleton(BlntAuthProps, instance=BlntAuthProps(ctrl_path, route_path))
            providers.add_provider(BolinetteAuthProvider)

        startup(cache=self.cache)(init_blnt_auth)
        return self
