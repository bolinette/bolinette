from abc import ABC
from bolinette import web
from bolinette.core import BolinetteContext, BolinetteExtension, ExtensionContext
from bolinette.data import DataContext


class WebContext(ExtensionContext):
    def __init__(self, ext: BolinetteExtension, context: BolinetteContext):
        super().__init__(ext, context)
        self.resources = web.BolinetteResources(context)
        self.docs = web.Documentation(context, context.registry.get(DataContext), self)


class WithWebContext(ABC):
    def __init__(self, web_ctx: WebContext) -> None:
        self.__web_ctx__ = web_ctx

    @property
    def web_ctx(self):
        return self.__web_ctx__
