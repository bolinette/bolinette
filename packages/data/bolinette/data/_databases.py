import importlib
import inspect
import re
from collections.abc import Callable
from typing import Any, ClassVar, Protocol

from escondite import Cache
from soupape import post_init
from soupape.extension import ResolutionContext

from bolinette.core import Logger
from bolinette.core.configuration import ConfigSection
from bolinette.data._config import DataSection
from bolinette.data.exceptions import DatabaseError


class Database(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def url(self) -> str: ...

    @property
    def echo(self) -> bool: ...

    @property
    def in_memory(self) -> bool: ...

    async def create_all(self) -> None: ...

    async def dispose(self) -> None: ...


class DatabaseSystem(Protocol):
    scheme: str
    python_package: str

    def create(self, name: str, url: str, echo: bool) -> Database: ...


def database_system[SystemT: DatabaseSystem](*, cache: Cache | None = None) -> Callable[[type[SystemT]], type[SystemT]]:
    def decorator(cls: type[SystemT]) -> type[SystemT]:
        Cache.with_fallback(cache).add(DatabaseManager.SYSTEM_CACHE_KEY, cls)
        return cls

    return decorator


class DatabaseManager:
    DBMS_RE = re.compile(r"^([^:]*://).*$")
    SYSTEM_CACHE_KEY: ClassVar[str] = "__blnt_data_db_system__"

    def __init__(self, cache: Cache, section: ConfigSection[DataSection], logger: "Logger[DatabaseManager]") -> None:
        self._cache = cache
        self._section = section
        self._logger = logger
        self._systems: list[DatabaseSystem] = []
        self._databases: dict[str, Database] = {}

    @property
    def systems(self) -> list[DatabaseSystem]:
        return [*self._systems]

    @property
    def databases(self) -> list[Database]:
        return [*self._databases.values()]

    def has_system(self, scheme: str) -> bool:
        return any(s.scheme == scheme for s in self._systems)

    def get_system(self, scheme: str) -> DatabaseSystem:
        return next(s for s in self._systems if s.scheme == scheme)

    def has_database(self, name: str) -> bool:
        return name in self._databases

    def get_database(self, name: str) -> Database:
        if name not in self._databases:
            raise DatabaseError("No database is defined in the configuration", connection=name)
        return self._databases[name]

    async def create_all(self) -> None:
        for database in self._databases.values():
            await database.create_all()

    async def dispose(self) -> None:
        for database in self._databases.values():
            await database.dispose()

    @post_init
    async def _init_systems(self, context: ResolutionContext) -> None:
        systems: list[DatabaseSystem] = []
        for cls in self._cache.get(self.SYSTEM_CACHE_KEY, hint=type[DatabaseSystem], raises=False):
            system: Any = context.require(cls)
            systems.append(await system if inspect.isawaitable(system) else system)
        if not systems:
            raise DatabaseError(f"No database system was registered with @{database_system.__name__}")
        self._systems.extend(sorted(systems, key=lambda s: s.scheme))

    @post_init
    def _init_databases(self) -> None:
        for db_config in self._section.value.databases:
            if db_config.name in self._databases:
                raise DatabaseError("Database name is used twice in the configuration", connection=db_config.name)
            re_match = self.DBMS_RE.match(db_config.url)
            if re_match is None:
                raise DatabaseError(f"Invalid URL '{db_config.url}'", connection=db_config.name)
            scheme = re_match.group(1)
            if not self.has_system(scheme):
                raise DatabaseError(
                    f"Database system supporting scheme '{scheme}' was not found", connection=db_config.name
                )
            system = self.get_system(scheme)
            try:
                importlib.import_module(system.python_package)
            except ModuleNotFoundError as e:
                raise DatabaseError(
                    f"Python package '{system.python_package}' was not found",
                    system=system.scheme,
                    connection=db_config.name,
                ) from e
            self._databases[db_config.name] = system.create(db_config.name, db_config.url, db_config.echo)
            self._logger.debug(f"Registered connection '{db_config.name}' on {scheme}")
