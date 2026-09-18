from typing import ClassVar

from escondite import Cache

from bolinette.data._databases import Database
from bolinette.data.relational._base import get_declarative_bases
from bolinette.data.relational._database import AbstractDatabase


class RelationalSystem:
    scheme: ClassVar[str]
    python_package: ClassVar[str]
    database: ClassVar[type[AbstractDatabase]]

    def __init__(self, cache: Cache) -> None:
        self._cache = cache

    def create(self, name: str, url: str, echo: bool) -> Database:
        return self.database(name, url, echo, get_declarative_bases(self._cache, name))
