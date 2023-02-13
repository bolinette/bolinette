from collections.abc import AsyncIterable
from typing import Generic, Self, TypeVar, Callable, Any

from sqlalchemy import Select, desc as sql_desc, select
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
    def __init__(
        self,
        rel_def: RelationalDefinition[EntityT],
        session: ScopedSession[EntityT],
        query: Select | None = None,
    ):
        self._rel_def = rel_def
        self._session = session
        self._query = query if query is not None else select(self._rel_def)

    def where(self, function: Callable[[EntityT], bool]) -> Self:
        return RelationalQuery(
            self._rel_def,
            self._session,
            self._query.where(function(self._rel_def)),  # type: ignore
        )

    def order_by(self, column: str, *, desc: bool = False) -> Self:
        col = getattr(self._rel_def, column)
        if desc:
            col = sql_desc(col)
        return RelationalQuery(self._rel_def, self._session, self._query.order_by(col))

    def offset(self, offset: int) -> Self:
        return RelationalQuery(self._rel_def, self._session, self._query.offset(offset))

    def limit(self, limit: int) -> Self:
        return RelationalQuery(self._rel_def, self._session, self._query.limit(limit))

    def include(self, function: Callable[[EntityT], Any]) -> Self:
        return RelationalQuery(
            self._rel_def,
            self._session,
            self._query.options(selectinload(function(self._rel_def))),  # type: ignore
        )

    async def all(self) -> AsyncIterable[EntityT]:
        result = await self._session.execute(self._query)
        for scalar in result.scalars():
            yield scalar
