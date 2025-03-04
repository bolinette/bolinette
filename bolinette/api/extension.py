from bolinette import data, web
from bolinette.core import Cache


class ApiExtension:
    def __init__(self, cache: Cache) -> None:
        self.name = "api"
        self.dependencies = [data, web]
