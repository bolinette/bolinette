from typing import Any

from bolinette.core import Cache, meta
from bolinette.core.exceptions import InitError
from bolinette.core.injection import Injection, init_method
from bolinette.core.logger import Logger
from bolinette.data import DatabaseManager
from bolinette.data.exceptions import EntityError
from bolinette.data.relational import (
    AbstractDatabase,
    DeclarativeBase,
    DeclarativeMeta,
    EntityMeta,
    Repository,
)
from bolinette.data.relational.repository import RepositoryMeta
from bolinette.data.relational.service import Service, ServiceMeta


class EntityManager:
    def __init__(self) -> None:
        self._entities: set[type[DeclarativeBase]] = set()
        self._engines: dict[type[DeclarativeBase], AbstractDatabase] = {}

    @property
    def entities(self) -> set[type[DeclarativeBase]]:
        return {*self._entities}

    @property
    def engines(self) -> dict[type[DeclarativeBase], AbstractDatabase]:
        return {**self._engines}

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
            self._entities.add(entity)
            found = False
            for base, engine in self._engines.items():
                if issubclass(entity, base):
                    if found:
                        raise EntityError(f"Entity {entity} cannot inherit from multiple declarative bases")
                    meta.set(entity, engine, cls=AbstractDatabase)
                    found = True
            if not found:
                raise EntityError(f"Entity {entity} has no known bases as its parents")

    @init_method
    def _init_repositories(self, cache: Cache, inject: Injection) -> None:
        repo_classes = cache.get(RepositoryMeta, hint=type[Repository[Any]], raises=False)
        custom_repos: set[type[DeclarativeBase]] = set()
        for repo_cls in repo_classes:
            repo_meta: RepositoryMeta[Any] = meta.get(repo_cls, RepositoryMeta)
            base_t = next((b for b in repo_meta.repo_t.bases if b.cls is Repository), None)
            if base_t is None:
                raise InitError(f"Repository {repo_meta.repo_t}, class must inherit from Repository[Entity]")
            entity_cls = base_t.vars[0]
            if entity_cls not in self._entities:
                raise InitError(f"Repository {repo_cls}, entity {entity_cls} is not a registered entity type")
            inject.add(repo_cls, "scoped")
            inject.add(repo_cls, "scoped", super_cls=Repository[entity_cls])
            custom_repos.add(entity_cls)

        for entity in self._entities:
            if entity not in custom_repos:
                inject.add(Repository[entity], "scoped")

    @init_method
    def _init_services(self, cache: Cache, inject: Injection) -> None:
        service_classes = cache.get(ServiceMeta, hint=type[Service[Any]], raises=False)
        custom_services: set[type[DeclarativeBase]] = set()
        for service_cls in service_classes:
            service_meta: ServiceMeta[Any] = meta.get(service_cls, ServiceMeta)
            base_t = next((b for b in service_meta.service_t.bases if b.cls is Service), None)
            if base_t is None:
                raise InitError(f"Service {service_meta.service_t}, class must inherit from Service[Entity]")
            entity_cls = base_t.vars[0]
            if entity_cls not in self._entities:
                raise InitError(f"Service {service_cls}, entity {entity_cls} is not a registered entity type")
            inject.add(service_cls, "scoped")
            inject.add(service_cls, "scoped", super_cls=Service[entity_cls])
            custom_services.add(entity_cls)

        for entity in self._entities:
            if entity not in custom_services:
                inject.add(Service[entity], "scoped")

    def is_entity_type(self, cls: type[Any]) -> bool:
        return cls in self._entities

    async def create_all(self) -> None:
        for engine in self._engines.values():
            await engine.create_all()


async def create_tables_for_memory_db(entities: EntityManager, logger: Logger[EntityManager]) -> None:
    for engine in entities.engines.values():
        if engine.in_memory:
            logger.info(f"Creating tables for connection {engine.uri}")
            await engine.create_all()
