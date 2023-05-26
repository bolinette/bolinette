from typing import Any, Generic, TypeVar

from bolinette.ext.data.relational import DeclarativeBase, Repository
from bolinette.mapping import Mapper

EntityT = TypeVar("EntityT", bound=DeclarativeBase)


class Service(Generic[EntityT]):
    def __init__(self, entity: type[EntityT], repository: Repository[EntityT], mapper: Mapper) -> None:
        self._entity = entity
        self._repository = repository
        self._mapper = mapper

    def create(self, payload: Any) -> EntityT:
        entity = self._mapper.map(type(payload), self._entity, payload)
        self._repository.add(entity)
        self.validate_entity(entity)
        return entity

    def update(self, entity: EntityT, payload: Any) -> EntityT:
        self._mapper.map(type(payload), self._entity, payload, entity)
        self.validate_entity(entity)
        return entity

    def validate_entity(self, entity: EntityT) -> None:
        pass
