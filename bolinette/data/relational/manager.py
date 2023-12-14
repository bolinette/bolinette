from typing import Any

from sqlalchemy import PrimaryKeyConstraint, Table, UniqueConstraint

from bolinette.core import Cache, meta, startup
from bolinette.core.injection import Injection, init_method
from bolinette.core.logger import Logger
from bolinette.data import DatabaseManager
from bolinette.data.exceptions import DataError, EntityError
from bolinette.data.relational import (
    AbstractDatabase,
    DeclarativeBase,
    DeclarativeMeta,
    EntityMeta,
    Repository,
)
from bolinette.data.relational.repository import RepositoryMeta


class EntityManager:
    def __init__(self) -> None:
        self._entities: list[type[DeclarativeBase]] = []
        self._engines: dict[type[DeclarativeBase], AbstractDatabase] = {}

    @property
    def entities(self) -> list[type[DeclarativeBase]]:
        return list(self._entities)

    @property
    def engines(self) -> dict[type[DeclarativeBase], AbstractDatabase]:
        return dict(self._engines)

    @init_method
    def _init_engines(self, cache: Cache, databases: DatabaseManager) -> None:
        for base in cache.get(DeclarativeMeta, hint=type[DeclarativeBase], raises=False):
            _m = meta.get(base, DeclarativeMeta)
            if not databases.has_connection(_m.name):
                raise EntityError(f"No '{_m.name}' database connection defined in environment")
            conn = databases.get_connection(_m.name)
            if not issubclass(conn.manager, AbstractDatabase):
                raise EntityError(f"Database connection '{_m.name}' is not a relational system")
            self._engines[base] = conn.manager(base, conn.name, conn.url, conn.echo)

    @init_method
    def _init_entities(self, cache: Cache) -> None:
        for entity in cache.get(EntityMeta, hint=type[DeclarativeBase], raises=False):
            self._entities.append(entity)
            found = False
            for base, engine in self._engines.items():
                if issubclass(entity, base):
                    if found:
                        raise EntityError(f"Entity {entity} cannot inherit from multiple declarative bases")
                    meta.set(entity, engine, cls=AbstractDatabase)
                    found = True
            if not found:
                raise EntityError(f"Entity {entity} has no known bases as its parents")
            entity_key = meta.get(entity, EntityMeta).entity_key
            if not isinstance(entity.__table__, Table):
                raise EntityError("Could not determine entity key", entity=entity)
            for constraint in entity.__table__.constraints:
                if not isinstance(constraint, UniqueConstraint | PrimaryKeyConstraint):
                    continue
                if entity_key == list(constraint):
                    break
            else:
                raise EntityError("Entity key does not match with any unique constraint", entity=entity)

    @init_method
    def _init_repositories(self, cache: Cache, inject: Injection) -> None:
        repo_classes = cache.get(RepositoryMeta, hint=type[Repository[Any]], raises=False)
        used_classes: set[type[Repository[Any]]] = set()
        for entity in self._entities:
            for repo_class in repo_classes:
                repo_meta: RepositoryMeta[Any] = meta.get(repo_class, RepositoryMeta)
                if repo_meta.entity is entity:
                    inject.add(repo_class, "scoped")
                    inject.add(repo_class, "scoped", super_cls=Repository[entity])
                    used_classes.add(repo_class)
            else:
                inject.add(Repository[entity], "scoped")
        if len(used_classes) != len(repo_classes):
            raise DataError(f"Repository {repo_classes[0]} was not used with any registered entity")

    def is_entity_type(self, cls: type[Any]) -> bool:
        return cls in self._entities

    async def create_all(self) -> None:
        for engine in self._engines.values():
            await engine.create_all()


@startup
async def create_tables_for_memory_db(entities: EntityManager, logger: Logger[EntityManager]) -> None:
    for engine in entities.engines.values():
        if engine.in_memory:
            logger.info(f"Creating tables for connection {engine.uri}")
            await engine.create_all()
