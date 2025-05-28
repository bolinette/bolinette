from bolinette import data, web
from bolinette.core import Cache
from bolinette.core.extension import Extension, ExtensionModule


class ApiExtension:
    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self.name: str = "api"
        self.dependencies: list[ExtensionModule[Extension]] = [data, web]
