import re
import sys
from collections.abc import Callable
from typing import Protocol, TypeVar

from bolinette import Cache, init_method, injectable
from bolinette.ext.data import DataSection, __data_cache__
from bolinette.ext.data.database import RelationalDatabase
from bolinette.ext.data.exceptions import DatabaseError
from bolinette.ext.data.manager import EntityManager, TableDefinition


@injectable(cache=__data_cache__)
class DatabaseManager:
    DBMS_RE = re.compile(r"^([^:]*://).*$")

    def __init__(
        self, cache: Cache, section: DataSection, entities: EntityManager
    ) -> None:
        self._cache = cache
        self._section = section
        self._entities = entities
        self._engines: dict[str, RelationalDatabase] = {}

    @init_method
    def init(self) -> None:
        self._init_db_engines()
        self._init_tables()

    def _init_db_engines(self) -> None:
        cached_type = type[DatabaseSystem]
        systems = [t() for t in self._cache[DatabaseSystem, cached_type]]
        if not systems:
            raise DatabaseError(
                f"No system was registered with @{database_system.__name__}"
            )
        for db_config in self._section.databases:
            re_match = DatabaseManager.DBMS_RE.match(db_config.url)
            if re_match is None:
                raise DatabaseError(
                    f"Database connection '{db_config.name}': Invalid URL '{db_config.url}'"
                )
            scheme = re_match.group(1)
            for system in systems:
                if scheme == system.scheme:
                    db_system = system
                    break
            else:
                raise DatabaseError(
                    f"Database system supporting scheme '{scheme}' was not found"
                )
            if db_system.python_package not in sys.modules:
                raise DatabaseError(
                    f"Python package '{db_system.python_package}' was not found",
                    connection=scheme,
                )
            db_manager = db_system.manager(db_config.url, db_config.echo)
            self._engines[db_config.name] = db_manager

    def _init_tables(self) -> None:
        table_per_engine: dict[RelationalDatabase, dict[str, TableDefinition]] = {}
        for entity, table_def in self._entities.definitions.items():
            if table_def.database not in self._engines:
                raise DatabaseError(
                    f"No '{table_def.database}' database registered", entity=entity
                )
            engine = self._engines[table_def.database]
            if engine not in table_per_engine:
                table_per_engine[engine] = {}
            table_per_engine[engine][table_def.name] = table_def
        for engine, table_defs in table_per_engine.items():
            engine.init_tables(table_defs)


class DatabaseSystem(Protocol):
    scheme: str
    python_package: str
    manager: type[RelationalDatabase]

    def __init__(self) -> None:
        pass


SystemT = TypeVar("SystemT", bound=DatabaseSystem)


def database_system(
    *, cache: Cache | None = None
) -> Callable[[type[SystemT]], type[SystemT]]:
    def decorator(cls: type[SystemT]) -> type[SystemT]:
        (cache or __data_cache__).add(DatabaseSystem, cls)
        return cls

    return decorator
