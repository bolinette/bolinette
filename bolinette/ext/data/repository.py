from collections.abc import AsyncIterable
from typing import Generic, TypeVar

from bolinette import init_method
from bolinette.ext.data import Entity
from bolinette.ext.data.queries import BaseQuery, RelationalDefinition, RelationalQueryBuilder
from bolinette.ext.data.sessions import ScopedSession

EntityT = TypeVar("EntityT", bound=Entity)


class Repository(Generic[EntityT]):
    def __init__(self) -> None:
        self._entity: type[EntityT]
        self._rel_def: RelationalDefinition[EntityT]
        self._query_builder: RelationalQueryBuilder

    @init_method
    def init(
        self, entity: type[EntityT], rel_def: RelationalDefinition[EntityT], session: ScopedSession[EntityT]
    ) -> None:
        self._entity = entity
        self._rel_def = rel_def
        self._query_builder = RelationalQueryBuilder(entity, rel_def, session)

    def query(self) -> BaseQuery[EntityT]:
        return self._query_builder.query()

    def find_all(self) -> AsyncIterable[EntityT]:
        return self._query_builder.query().all()
