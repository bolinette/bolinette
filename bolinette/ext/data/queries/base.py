from abc import ABC, abstractmethod
from collections.abc import AsyncIterable, Callable
from typing import Any, Generic, Self, TypeVar

from bolinette.ext.data import Entity

EntityT = TypeVar("EntityT", bound=Entity)


QueryT = TypeVar("QueryT", bound="BaseQuery")


class BaseQuery(ABC, Generic[EntityT]):
    def __init__(self):
        self._wheres: list[Callable[[EntityT], bool]] = []
        self._order_by: list[tuple[str, bool]] = []
        self._limit: int | None = None
        self._offset = 0
        self._includes: list[Callable[[EntityT], Any]] = []

    def _base_clone(self, query: QueryT) -> QueryT:
        query._wheres = list(self._wheres)
        query._order_by = list(self._order_by)
        query._limit = self._limit
        query._offset = self._offset
        return query

    @abstractmethod
    def _clone(self) -> Self:
        pass

    def _where_func(self, function: Callable[[EntityT], bool]) -> Self:
        self._wheres.append(function)
        return self

    def where(self, function: Callable[[EntityT], bool]) -> Self:
        return self._clone()._where_func(function)

    def _order_by_func(self, column: str, *, desc: bool = False) -> Self:
        self._order_by.append((column, desc))
        return self

    def order_by(self, column: str, *, desc: bool = False) -> Self:
        return self._clone()._order_by_func(column, desc=desc)

    def _offset_func(self, offset: int) -> Self:
        self._offset = offset
        return self

    def offset(self, offset: int) -> Self:
        return self._clone()._offset_func(offset)

    def _limit_func(self, limit: int) -> Self:
        self._limit = limit
        return self

    def limit(self, limit: int) -> Self:
        return self._clone()._limit_func(limit)

    def _include_func(self, function: Callable[[EntityT], Any]) -> Self:
        self._includes.append(function)
        return self

    def include(self, function: Callable[[EntityT], Any]) -> Self:
        return self._clone()._include_func(function)

    @abstractmethod
    def all(self) -> AsyncIterable[EntityT]:
        ...
