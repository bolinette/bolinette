from collections.abc import AsyncIterable
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from bolinette.ext.data import Entity
from bolinette.ext.data.queries import BaseQuery, RelationalQueryBuilder

EntityT = TypeVar("EntityT", bound=Entity)


class Repository(Generic[EntityT]):
    def __init__(
        self,
        entity: type[EntityT],
        orm_def: type[DeclarativeBase],
        session: AsyncSession,
    ) -> None:
        self._entity = entity
        self._orm_def = orm_def
        self._query_builder = RelationalQueryBuilder(entity, orm_def, session)

    def query(self) -> BaseQuery[EntityT]:
        return self._query_builder.query()

    def find_all(self) -> AsyncIterable[EntityT]:
        return self._query_builder.query().all()
