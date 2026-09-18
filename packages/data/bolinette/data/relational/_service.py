from collections.abc import Callable
from typing import Any, ClassVar, Literal, overload

from escondite import Cache
from muotti import Mapper
from peritype import TWrap, wrap_type
from sqlalchemy.orm import DeclarativeBase

from bolinette.data._mapping import validate_entity
from bolinette.data.relational._repository import Repository


class Service[EntityT: DeclarativeBase]:
    def __init__(self, entity_t: TWrap[EntityT], repository: Repository[EntityT], mapper: Mapper) -> None:
        self._entity: type[EntityT] = entity_t.origin
        self._repository = repository
        self._mapper = mapper

    @property
    def entity(self) -> type[EntityT]:
        return self._entity

    @property
    def repository(self) -> Repository[EntityT]:
        return self._repository

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[True] = True) -> EntityT: ...
    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[False]) -> EntityT | None: ...
    async def get_by_primary(self, *values: Any, raises: bool = True) -> EntityT | None:
        if raises is False:
            return await self._repository.get_by_primary(*values, raises=False)
        return await self._repository.get_by_primary(*values)

    async def get_all(self) -> list[EntityT]:
        return [e async for e in self._repository.find_all()]

    def create(self, payload: Any, *, validate: bool = False) -> EntityT:
        entity = self._mapper.map(self._entity, payload, validate=validate)
        validate_entity(entity)
        self._repository.add(entity)
        return entity

    def update(self, entity: EntityT, payload: Any, *, validate: bool = False) -> EntityT:
        self._mapper.merge(payload, entity, validate=validate)
        validate_entity(entity)
        return entity

    async def delete(self, entity: EntityT) -> EntityT:
        await self._repository.delete(entity)
        return entity


class ServiceMeta:
    KEY: ClassVar[str] = "__blnt_data_service_meta__"


def service[ServiceT: Service[Any]](*, cache: Cache | None = None) -> Callable[[type[ServiceT]], type[ServiceT]]:
    def decorator(cls: type[ServiceT]) -> type[ServiceT]:
        Cache.with_fallback(cache).add(ServiceMeta.KEY, wrap_type(cls))
        return cls

    return decorator
