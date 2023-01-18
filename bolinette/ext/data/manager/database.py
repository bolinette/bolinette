import re
from collections.abc import Callable
from typing import Protocol, TypeVar
import importlib

from bolinette import Cache, init_method, injectable, meta, Injection
from bolinette.ext.data import DataSection, __data_cache__, Entity, Repository
from bolinette.ext.data.database import RelationalDatabase
from bolinette.ext.data.exceptions import DatabaseError
from bolinette.ext.data.manager import EntityManager, TableDefinition


@injectable(cache=__data_cache__, strategy="singleton")
class DatabaseManager:
    DBMS_RE = re.compile(r"^([^:]*://).*$")

    def __init__(
        self, cache: Cache, section: DataSection, entities: EntityManager, inject: Injection
    ) -> None:
        self._cache = cache
        self._section = section
        self._entities = entities
        self._engines: dict[str, RelationalDatabase] = {}
        self._inject = inject

    def get_engine(self, name: str) -> RelationalDatabase:
        return self._engines[name]

    @init_method
    def init(self) -> None:
        self._init_db_engines()
        self._init_tables()
        self._init_repositories()

    def _init_db_engines(self) -> None:
        systems = [
            t()
            for t in self._cache.get(
                DatabaseSystem, hint=type[DatabaseSystem], raises=False
            )
        ]
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
            try:
                importlib.import_module(db_system.python_package)
            except ModuleNotFoundError:
                raise DatabaseError(
                    f"Python package '{db_system.python_package}' was not found",
                    connection=scheme,
                )
            db_manager = db_system.manager(
                db_config.name, db_config.url, db_config.echo
            )
            self._engines[db_config.name] = db_manager

    def _init_tables(self) -> None:
        sorted_tables: dict[
            RelationalDatabase, dict[type[Entity], TableDefinition]
        ] = {}
        for entity, table_def in self._entities.definitions.items():
            if table_def.database not in self._engines:
                raise DatabaseError(
                    f"No '{table_def.database}' database registered", entity=entity
                )
            engine = self._engines[table_def.database]
            if engine not in sorted_tables:
                sorted_tables[engine] = {}
            sorted_tables[engine][table_def.entity] = table_def
            meta.set(entity, DatabaseMeta(engine))
        for engine, table_defs in sorted_tables.items():
            engine.init_tables(table_defs)

    def _init_repositories(self) -> None:
        for entity in self._entities.definitions:
            engine = meta.get(entity, DatabaseMeta).engine
            orm_def = engine.get_definition(entity)
            self._inject.add(Repository[entity], "scoped", kwargs={'orm_def': orm_def})


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


class DatabaseMeta:
    def __init__(self, engine: RelationalDatabase) -> None:
        self.engine = engine
