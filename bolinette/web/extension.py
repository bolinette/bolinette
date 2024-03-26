from typing import Self, override

from bolinette import core
from bolinette.core import Cache, startup
from bolinette.core.extension import Extension
from bolinette.core.injection import Injection, injectable
from bolinette.web.config import WebConfig
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

        startup(cache=cache)(init_web_ext)

    def use_sockets(self) -> Self:
        self.config.use_sockets = True
        return self


web_ext = WebExtension()


async def init_web_ext(inject: Injection) -> None:
    inject.add(WebExtension, strategy="singleton", instance=web_ext)
    inject.add(WebConfig, strategy="singleton", instance=web_ext.config)
