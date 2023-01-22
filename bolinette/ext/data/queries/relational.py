from collections.abc import AsyncIterable
from typing import Generic, Self, TypeVar

from sqlalchemy import Select, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, selectinload

from bolinette.ext.data import Entity
from bolinette.ext.data.queries import BaseQuery

EntityT = TypeVar("EntityT", bound=Entity)


class RelationalQueryBuilder(Generic[EntityT]):
    def __init__(
        self,
        entity: type[EntityT],
        orm_def: type[DeclarativeBase],
        session: AsyncSession,
    ) -> None:
        self._entity = entity
        self._orm_def = orm_def
        self._session = session

    def query(self) -> BaseQuery[EntityT]:
        return RelationalQuery(self._orm_def, self._session)


class RelationalQuery(BaseQuery[EntityT], Generic[EntityT]):
    def __init__(self, orm_def: type[DeclarativeBase], session: AsyncSession):
        super().__init__()
        self._orm_def = orm_def
        self._session = session

    def _clone(self) -> Self:
        return self._base_clone(RelationalQuery(self._orm_def, self._session))

    async def all(self) -> AsyncIterable[EntityT]:
        for scalar in (await self._session.execute(self._build_query())).scalars():  # type: ignore
            yield scalar

    def _query(self) -> Select:
        return select(self._orm_def)

    def _build_query(self):
        query = self._query()
        for function in self._wheres:
            query = query.where(function(self._orm_def))  # type: ignore
        for column, order in self._order_by:
            if hasattr(self._orm_def, column):
                col = getattr(self._orm_def, column)
                if order:
                    col = desc(col)
                query = query.order_by(col)
        query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)
        for include in self._includes:
            query = query.options(selectinload(include(self._orm_def)))  # type: ignore
        return query
