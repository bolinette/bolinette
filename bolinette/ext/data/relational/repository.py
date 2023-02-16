from collections.abc import AsyncIterable
from typing import Generic, TypeVar, overload, Literal, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import TypedReturnsRows
from sqlalchemy.sql.elements import NamedColumn

from bolinette.ext.data.relational import DeclarativeBase
from bolinette.ext.data.exceptions import EntityNotFoundError

EntityT = TypeVar("EntityT", bound=DeclarativeBase)


class Repository(Generic[EntityT]):
    def __init__(self, entity: type[EntityT], session: AsyncSession) -> None:
        self._entity = entity
        self._session = session
        self._primary_key = entity.__table__.primary_key


    async def iterate(self, statement: TypedReturnsRows[tuple[EntityT]]) -> AsyncIterable[EntityT]:
        result = await self._session.execute(statement)
        for row in result.scalars():
            yield row

    @overload
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: Literal[True] = True) -> EntityT:
        ...

    @overload
    async def first(self, statement: TypedReturnsRows[tuple[EntityT]], *, raises: Literal[False]) -> EntityT | None:
        ...

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
        ...

    @overload
    async def get_by_primary(self, *values: Any, raises: Literal[False]) -> EntityT | None:
        ...

    async def get_by_primary(self, *values: Any, raises: bool = True) -> EntityT | None:
        query = select(self._entity)
        for col, value in zip(self._primary_key, values):
            query = query.where(col == value)
        return await self.first(query, raises=raises)  # type: ignore

    def add(self, entity: EntityT) -> None:
        self._session.add(entity)

    async def delete(self, entity: EntityT) -> None:
        await self._session.delete(entity)

    async def commit(self) -> None:
        await self._session.commit()
