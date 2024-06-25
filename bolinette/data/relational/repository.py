from collections.abc import AsyncIterable, Callable, Iterable
from typing import Any, Literal, overload

from sqlalchemy import select
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.sql.selectable import TypedReturnsRows

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.injection import init_method
from bolinette.core.types import Type
from bolinette.data.exceptions import DataError, EntityNotFoundError
from bolinette.data.relational import DeclarativeBase, EntitySession


class Repository[EntityT: DeclarativeBase]:
    def __init__(self) -> None:
        self._entity: type[EntityT]
        self._session: EntitySession[EntityT]
        self._primary_key: Iterable[NamedColumn[Any]]

    @init_method
    def _init_session(self, entity: type[EntityT], session: EntitySession[EntityT]) -> None:
        self._entity = entity
        self._session = session
        self._primary_key = self._entity.__table__.primary_key

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

    def add(self, entity: EntityT) -> None:
        self._session.add(entity)

    async def delete(self, entity: EntityT) -> None:
        await self._session.delete(entity)

    async def commit(self) -> None:
        await self._session.commit()


class RepositoryMeta[RepoT: Repository[Any]]:
    def __init__(self, repo_t: Type[RepoT]) -> None:
        self.repo_t = repo_t


def repository[RepoT: Repository[Any]](*, cache: Cache | None = None) -> Callable[[type[RepoT]], type[RepoT]]:
    def decorator(cls: type[RepoT]) -> type[RepoT]:
        meta.set(cls, RepositoryMeta(Type(cls)))
        (cache or __user_cache__).add(RepositoryMeta, cls)
        return cls

    return decorator
