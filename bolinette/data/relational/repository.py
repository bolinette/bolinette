from collections.abc import AsyncIterable, Callable
from typing import Any, Literal, TypeVar, overload

from sqlalchemy import select
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.sql.selectable import TypedReturnsRows

from bolinette.core import Cache, __user_cache__, meta
from bolinette.data.exceptions import DataError, EntityNotFoundError
from bolinette.data.relational import DeclarativeBase, EntityMeta, EntitySession


class Repository[EntityT: DeclarativeBase]:
    def __init__(self, entity: type[EntityT], session: EntitySession[EntityT]) -> None:
        self._entity = entity
        self._session = session
        self._primary_key = self._entity.__table__.primary_key
        self._entity_key = meta.get(self._entity, EntityMeta).entity_key

    @property
    def primary_key(self) -> list[NamedColumn[Any]]:
        return list(self._primary_key)

    async def iterate(self, statement: TypedReturnsRows[tuple[EntityT]]) -> AsyncIterable[EntityT]:
        result = await self._session.execute(statement)
        for row in result.scalars():
            yield row

    @overload
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: Literal[True] = True) -> EntityT:
        pass

    @overload
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: Literal[False]) -> EntityT | None:
        pass

    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: bool = True) -> EntityT | None:
        result = await self._session.execute(statement)
        entity = result.scalar_one_or_none()
        if entity is None and raises:
            raise EntityNotFoundError(self._entity)
        return entity

    def find_all(self) -> AsyncIterable[EntityT]:
        return self.iterate(select(self._entity))

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[True] = True) -> EntityT:
        pass

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[False]) -> EntityT | None:
        pass

    async def get_by_primary(self, *values: Any, raises: bool = True) -> EntityT | None:
        if (val_l := len(values)) != (prim_l := len(list(self._primary_key))):
            raise DataError(f"Primary key of {self._entity} has {prim_l} columns, but {val_l} values were provided")
        query = select(self._entity)
        for col, value in zip(self._primary_key, values, strict=True):
            query = query.where(col == value)
        return await self.first(query, raises=raises)  # pyright: ignore

    @overload
    async def get_by_key(self, *values: Any, raises: Literal[True] = True) -> EntityT:
        pass

    @overload
    async def get_by_key(self, *values: Any, raises: Literal[False]) -> EntityT | None:
        pass

    async def get_by_key(self, *values: Any, raises: bool = True) -> EntityT | None:
        if (val_l := len(values)) != (key_l := len(list(self._entity_key))):
            raise DataError(f"Entity key of {self._entity} has {key_l} columns, but {val_l} values were provided")
        query = select(self._entity)
        for col, value in zip(self._entity_key, values, strict=True):
            query = query.where(col == value)
        return await self.first(query, raises=raises)  # pyright: ignore

    def add(self, entity: EntityT) -> None:
        self._session.add(entity)

    async def delete(self, entity: EntityT) -> None:
        await self._session.delete(entity)

    async def commit(self) -> None:
        await self._session.commit()


class RepositoryMeta[EntityT: DeclarativeBase]:
    def __init__(self, entity: type[EntityT]) -> None:
        self.entity = entity


EntityT = TypeVar("EntityT", bound=DeclarativeBase)
RepoT = TypeVar("RepoT", bound=Repository[EntityT])  # pyright: ignore


def repository(entity: type[EntityT], *, cache: Cache | None = None) -> Callable[[type[RepoT]], type[RepoT]]:
    def decorator(cls: type[RepoT]) -> type[RepoT]:
        meta.set(cls, RepositoryMeta(entity))
        (cache or __user_cache__).add(RepositoryMeta, cls)
        return cls

    return decorator
