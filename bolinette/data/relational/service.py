from typing import Any

from sqlalchemy import Table

from bolinette.core.mapping import Mapper
from bolinette.data.exceptions import ColumnNotNullableError, WrongColumnTypeError
from bolinette.data.relational import DeclarativeBase, Repository


class Service[EntityT: DeclarativeBase]:
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
        table = entity.__table__
        assert isinstance(table, Table)
        for col_name, column in table.columns.items():
            value = getattr(entity, col_name, None)
            if not column.nullable and value is None:
                raise ColumnNotNullableError(self._entity, col_name)
            if column.nullable and value is None:
                continue
            if not issubclass(type(value), column.type.python_type):
                raise WrongColumnTypeError(self._entity, col_name, value, column.type.python_type)
