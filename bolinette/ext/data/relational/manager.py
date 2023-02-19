from typing import Any

from bolinette import Cache, Injection, init_method, injectable, meta
from bolinette.ext.data import DatabaseManager, __data_cache__
from bolinette.ext.data.exceptions import EntityError
from bolinette.ext.data.relational import DeclarativeBase, DeclarativeMeta, EntityMeta, RelationalDatabase, Repository, SessionManager


@injectable(cache=__data_cache__, strategy="singleton")
class EntityManager:
    def __init__(self, databases: DatabaseManager) -> None:
        self._databases = databases
        self._entities: list[type[DeclarativeBase]] = []
        self._engines: dict[type[DeclarativeBase], RelationalDatabase] = {}

    @init_method
    def _init_bases(self, cache: Cache) -> None:
        for base in cache.get(DeclarativeMeta, hint=type[DeclarativeBase]):
            _m = meta.get(base, DeclarativeMeta)
            if not self._databases.has_connection(_m.name):
                raise EntityError(f"No '{_m.name}' database connection defined in environment")
            conn = self._databases.get_connection(_m.name)
            if conn.manager is not RelationalDatabase:
                raise EntityError(f"Database connection '{_m.name}' is not a relational system")
            self._engines[base] = RelationalDatabase(base, conn.name, conn.url, conn.echo)

    @init_method
    def _init_entities(self, cache: Cache) -> None:
        for entity in cache.get(EntityMeta, hint=type[DeclarativeBase]):
            self._entities.append(entity)
            for base, engine in self._engines.items():
                if issubclass(entity, base):
                    meta.set(entity, engine, cls=RelationalDatabase)

    @init_method
    def _init_repositories(self, inject: Injection) -> None:
        for entity in self._entities:
            inject.add(Repository[entity], "scoped")

    def is_entity_type(self, cls: type[Any]) -> bool:
        return cls in self._entities

    async def create_all(self) -> None:
        for engine in self._engines.values():
            await engine.create_all()

    def open_sessions(self, sessions: SessionManager) -> None:
        for engine in self._engines.values():
            engine.open_session(sessions)
