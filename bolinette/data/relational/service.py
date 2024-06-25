from collections.abc import Callable
from typing import Any, Literal, overload

from sqlalchemy import Table

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.mapping import Mapper
from bolinette.core.types import Type
from bolinette.data.exceptions import ColumnNotNullableError, WrongColumnTypeError
from bolinette.data.relational import DeclarativeBase, Repository


class Service[EntityT: DeclarativeBase]:
    def __init__(self, entity: type[EntityT], repository: Repository[EntityT], mapper: Mapper) -> None:
        self._entity = entity
        self._repository = repository
        self._mapper = mapper

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[True] = True) -> EntityT:
        pass

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[False]) -> EntityT | None:
        pass

    async def get_by_primary(self, *values: Any, raises: bool = True) -> EntityT | None:
        if raises is False:
            return await self._repository.get_by_primary(*values, raises=False)
        return await self._repository.get_by_primary(*values)

    async def get_all(self) -> list[EntityT]:
        return [e async for e in self._repository.find_all()]

    def create(self, payload: object) -> EntityT:
        entity = self._mapper.map(type(payload), self._entity, payload)
        self._repository.add(entity)
        self.validate_entity(entity)
        return entity

    def update(self, entity: EntityT, payload: object) -> EntityT:
        self._mapper.map(type(payload), self._entity, payload, entity)
        self.validate_entity(entity)
        return entity

    async def delete(self, entity: EntityT) -> EntityT:
        await self._repository.delete(entity)
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


class ServiceMeta[ServiceT: Service[DeclarativeBase]]:
    def __init__(self, service_t: Type[ServiceT]) -> None:
        self.service_t = service_t


def service[ServiceT: Service[Any]](*, cache: Cache | None = None) -> Callable[[type[ServiceT]], type[ServiceT]]:
    def decorator(cls: type[ServiceT]) -> type[ServiceT]:
        meta.set(cls, ServiceMeta(Type(cls)))
        (cache or __user_cache__).add(ServiceMeta, cls)
        return cls

    return decorator
