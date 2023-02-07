from collections.abc import AsyncIterable
from typing import Generic, Self, TypeVar

from sqlalchemy import Select, desc, select
from sqlalchemy.orm import selectinload

from bolinette.ext.data import Entity
from bolinette.ext.data.queries import BaseQuery
from bolinette.ext.data.sessions import ScopedSession

EntityT = TypeVar("EntityT", bound=Entity)


class RelationalDefinition(Generic[EntityT]):
    pass


class RelationalQueryBuilder(Generic[EntityT]):
    def __init__(
        self,
        entity: type[EntityT],
        rel_def: RelationalDefinition[EntityT],
        session: ScopedSession[EntityT],
    ) -> None:
        self._entity = entity
        self._rel_def = rel_def
        self._session = session

    def query(self) -> BaseQuery[EntityT]:
        return RelationalQuery(self._rel_def, self._session)


class RelationalQuery(BaseQuery[EntityT], Generic[EntityT]):
    def __init__(self, rel_def: RelationalDefinition[EntityT], session: ScopedSession[EntityT]):
        super().__init__()
        self._rel_def = rel_def
        self._session = session

    def _clone(self) -> Self:
        return self._base_clone(RelationalQuery(self._rel_def, self._session))

    async def all(self) -> AsyncIterable[EntityT]:
        result = await self._session.execute(self._build_query())
        for scalar in result.scalars():
            yield scalar

    def _query(self) -> Select:
        return select(self._rel_def)

    def _build_query(self):
        query = self._query()
        for function in self._wheres:
            query = query.where(function(self._rel_def))  # type: ignore
        for column, order in self._order_by:
            if hasattr(self._rel_def, column):
                col = getattr(self._rel_def, column)
                if order:
                    col = desc(col)
                query = query.order_by(col)
        query = query.offset(self._offset)
        if self._limit is not None:
            query = query.limit(self._limit)
        for include in self._includes:
            query = query.options(selectinload(include(self._rel_def)))  # type: ignore
        return query
