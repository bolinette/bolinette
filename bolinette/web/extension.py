from typing import Self, override

from bolinette import core
from bolinette.core import Cache, startup
from bolinette.core.command import command
from bolinette.core.environment import environment
from bolinette.core.extension import Extension
from bolinette.core.injection import Injection, injectable
from bolinette.web.auth import AuthProviders, BlntAuthConfig
from bolinette.web.commands import new_encryption_key, new_rsa_key
from bolinette.web.config import BlntAuthProps, WebConfig
from bolinette.web.resources import WebResources
from bolinette.web.ws import WebSocketHandler


class WebExtension(Extension):
    def __init__(self) -> None:
        super().__init__("web", [core])
        self.config = WebConfig()

    @override
    def add_cached(self, cache: Cache) -> None:
        injectable(strategy="singleton", cache=cache)(WebResources)
        injectable(strategy="singleton", cache=cache)(WebSocketHandler)
        injectable(strategy="singleton", cache=cache)(AuthProviders)

        startup(cache=cache)(init_web_ext)

        environment("blntauth", cache=cache)(BlntAuthConfig)

        command("auth new rsa", "Creates a new RSA key", cache=cache)(new_rsa_key)
        command("auth new encrypt", "Creates a new encryption key", cache=cache)(new_encryption_key)

    def use_sockets(self) -> Self:
        self.config.use_sockets = True
        return self

    def use_blnt_auth(self, ctrl_path: str = "auth", route_path: str = "") -> Self:
        self.config.blnt_auth = BlntAuthProps(ctrl_path, route_path)
        return self


web_ext = WebExtension()


async def init_web_ext(inject: Injection) -> None:
    inject.add_singleton(WebExtension, instance=web_ext)
    inject.add_singleton(WebConfig, instance=web_ext.config)
