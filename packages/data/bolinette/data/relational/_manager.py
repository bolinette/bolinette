from typing import Any

from escondite import Cache
from peritype import TWrap, wrap_type
from peritype.collections import TypeBag
from soupape import ServiceCollection, post_init
from sqlalchemy.orm import DeclarativeBase

from bolinette.core import meta
from bolinette.core.exceptions import InitError
from bolinette.data._databases import DatabaseManager
from bolinette.data.exceptions import DatabaseError, EntityError
from bolinette.data.relational._base import DeclarativeMeta
from bolinette.data.relational._database import AbstractDatabase
from bolinette.data.relational._repository import Repository, RepositoryMeta
from bolinette.data.relational._service import Service, ServiceMeta

_REPO_ANY_TW = wrap_type(Repository[Any])
_SERVICE_ANY_TW = wrap_type(Service[Any])


def _specialize(generic: Any, entity_tw: TWrap[Any]) -> Any:
    return generic[entity_tw.origin]


class EntityManager:
    def __init__(self) -> None:
        self._entities = TypeBag[DeclarativeBase]()
        self._engines: dict[str, AbstractDatabase] = {}
        self._entity_engines: dict[type[DeclarativeBase], AbstractDatabase] = {}

    @property
    def entities(self) -> set[TWrap[DeclarativeBase]]:
        return {*self._entities}

    @property
    def engines(self) -> dict[str, AbstractDatabase]:
        return {**self._engines}

    def is_entity_type(self, cls: type[Any]) -> bool:
        return wrap_type(cls) in self._entities

    def get_engine(self, entity: type[DeclarativeBase]) -> AbstractDatabase:
        if entity not in self._entity_engines:
            raise EntityError("Entity is not registered", entity=entity)
        return self._entity_engines[entity]

    def get_engine_by_name(self, name: str) -> AbstractDatabase:
        if name not in self._engines:
            raise DatabaseError("No relational engine is bound to this connection", connection=name)
        return self._engines[name]

    @post_init
    def _bind_bases(self, cache: Cache, databases: DatabaseManager) -> None:
        for base in cache.get(DeclarativeMeta.KEY, hint=type[DeclarativeBase], raises=False):
            base_meta: DeclarativeMeta = meta.get(base, DeclarativeMeta.KEY)
            if not databases.has_database(base_meta.name):
                raise EntityError(f"No '{base_meta.name}' database connection defined in the configuration")
            database = databases.get_database(base_meta.name)
            if not isinstance(database, AbstractDatabase):
                raise EntityError(f"Database connection '{base_meta.name}' is not a relational system")
            self._engines[database.name] = database
            for mapper in base.registry.mappers:
                entity: type[DeclarativeBase] = mapper.class_
                self._entities.add(wrap_type(entity))
                self._entity_engines[entity] = database


def discover_entities(cache: Cache) -> TypeBag[DeclarativeBase]:
    entities = TypeBag[DeclarativeBase]()
    for base in cache.get(DeclarativeMeta.KEY, hint=type[DeclarativeBase], raises=False):
        for mapper in base.registry.mappers:
            entities.add(wrap_type(mapper.class_))
    return entities


def register_relational_services(services: ServiceCollection, cache: Cache) -> None:
    entities = discover_entities(cache)
    for generic, generic_tw, meta_key, kind in (
        (Repository, _REPO_ANY_TW, RepositoryMeta.KEY, "Repository"),
        (Service, _SERVICE_ANY_TW, ServiceMeta.KEY, "Service"),
    ):
        custom: dict[TWrap[Any], TWrap[Any]] = {}
        for cls_tw in cache.get(meta_key, hint=TWrap[Any], raises=False):
            entity_tw = _generic_entity(cls_tw, generic_tw, kind, entities)
            if entity_tw in custom:
                raise InitError(
                    f"{kind} {cls_tw}, entity {entity_tw} already has {kind.lower()} {custom[entity_tw]}, "
                    f"only one {kind.lower()} can be registered for an entity"
                )
            services.add_scoped(cls_tw.origin)
            services.add_scoped(_specialize(generic, entity_tw), cls_tw.origin)
            custom[entity_tw] = cls_tw
        for entity_tw in entities:
            if entity_tw not in custom:
                services.add_scoped(_specialize(generic, entity_tw))


def _generic_entity(cls_tw: TWrap[Any], generic_tw: TWrap[Any], kind: str, entities: TypeBag[Any]) -> TWrap[Any]:
    base_tw = next((b for b in cls_tw.iter_bases() if b.matches(generic_tw)), None)
    if base_tw is None:
        raise InitError(f"{kind} {cls_tw}, class must inherit from {kind}[Entity]")
    entity_tw = base_tw.generic_params[0]
    if entity_tw not in entities:
        raise InitError(f"{kind} {cls_tw}, entity {entity_tw} is not a registered entity type")
    return entity_tw
