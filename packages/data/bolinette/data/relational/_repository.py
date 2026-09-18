from collections.abc import AsyncIterable, Callable, Iterable
from typing import Any, ClassVar, Literal, cast, overload

from escondite import Cache
from peritype import TWrap, wrap_type
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import NamedColumn
from sqlalchemy.sql.selectable import TypedReturnsRows

from bolinette.data import relational
from bolinette.data.exceptions import DataError, EntityNotFoundError
from bolinette.data.relational._session import EntitySession
from bolinette.data.relational._transaction import AsyncTransaction


class Repository[EntityT: DeclarativeBase]:
    def __init__(
        self, entity_t: TWrap[EntityT], entities: "relational.EntityManager", transaction: AsyncTransaction
    ) -> None:
        self._entity: type[EntityT] = entity_t.origin
        session = transaction.get(entities.get_engine(self._entity).name)
        self._session = cast(EntitySession[EntityT], session)
        self._primary_key: Iterable[NamedColumn[Any]] = self._entity.__table__.primary_key

    @property
    def entity(self) -> type[EntityT]:
        return self._entity

    @property
    def primary_key(self) -> list[NamedColumn[Any]]:
        return list(self._primary_key)

    async def iterate(self, statement: TypedReturnsRows[tuple[EntityT]]) -> AsyncIterable[EntityT]:
        result = await self._session.execute(statement)
        for row in result.scalars():
            yield row

    @overload
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: Literal[True] = True) -> EntityT: ...
    @overload
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: Literal[False]) -> EntityT | None: ...
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: bool = True) -> EntityT | None:
        result = await self._session.execute(statement)
        entity = result.scalars().first()
        if entity is None and raises:
            raise EntityNotFoundError(self._entity)
        return entity

    def find_all(self) -> AsyncIterable[EntityT]:
        return self.iterate(select(self._entity))

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[True] = True) -> EntityT: ...
    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[False]) -> EntityT | None: ...
    async def get_by_primary(self, *values: Any, raises: bool = True) -> EntityT | None:
        if (val_l := len(values)) != (prim_l := len(list(self._primary_key))):
            raise DataError(f"Primary key of {self._entity} has {prim_l} columns, but {val_l} values were provided")
        query = select(self._entity)
        for col, value in zip(self._primary_key, values, strict=True):
            query = query.where(col == value)
        return await self.first(query, raises=raises)

    def add(self, entity: EntityT) -> None:
        self._session.add(entity)

    async def delete(self, entity: EntityT) -> None:
        await self._session.delete(entity)

    async def flush(self) -> None:
        await self._session.flush()


class RepositoryMeta:
    KEY: ClassVar[str] = "__blnt_data_repo_meta__"


def repository[RepoT: Repository[Any]](*, cache: Cache | None = None) -> Callable[[type[RepoT]], type[RepoT]]:
    def decorator(cls: type[RepoT]) -> type[RepoT]:
        Cache.with_fallback(cache).add(RepositoryMeta.KEY, wrap_type(cls))
        return cls

    return decorator
