from abc import abstractmethod, ABC
from collections.abc import Callable
from typing import Any

from bolinette import abc, blnt, core


class BaseQueryBuilder(abc.WithContext, ABC):
    def __init__(self, model: 'core.Model', context: 'blnt.BolinetteContext'):
        abc.WithContext.__init__(self, context)
        self._model = model

    @abstractmethod
    def query(self) -> 'BaseQuery':
        pass

    @abstractmethod
    async def insert_entity(self, values):
        pass

    @abstractmethod
    async def update_entity(self, entity):
        pass

    @abstractmethod
    async def delete_entity(self, entity):
        pass


class BaseQuery(ABC):
    def __init__(self):
        self._filters_by: dict[str, Any] = {}
        self._filters: list[Callable[[Any], Any]] = []
        self._order_by: list[tuple[str, bool]] = []
        self._offset = 0
        self._limit: int | None = None

    def _base_clone(self, query: 'BaseQuery'):
        query._filters_by = dict(self._filters_by)
        query._filters = list(self._filters)
        query._order_by = list(self._order_by)
        query._limit = self._limit
        query._offset = self._offset

    @abstractmethod
    def _clone(self) -> 'BaseQuery':
        pass

    def _filter_by_func(self, **kwargs) -> 'BaseQuery':
        for key in kwargs:
            self._filters_by[key] = kwargs[key]
        return self

    def filter_by(self, **kwargs) -> 'BaseQuery':
        return self._clone()._filter_by_func(**kwargs)

    def _filter_func(self, function: Callable[[Any], Any]):
        self._filters.append(function)
        return self

    def filter(self, function: Callable[[Any], Any]):
        return self._clone()._filter_func(function)

    def _order_by_func(self, column: str, *, desc: bool = False) -> 'BaseQuery':
        self._order_by.append((column, desc))
        return self

    def order_by(self, column: str, *, desc: bool = False) -> 'BaseQuery':
        return self._clone()._order_by_func(column, desc=desc)

    def _offset_func(self, offset: int) -> 'BaseQuery':
        self._offset = offset
        return self

    def offset(self, offset: int) -> 'BaseQuery':
        return self._clone()._offset_func(offset)

    def _limit_func(self, limit: int) -> 'BaseQuery':
        self._limit = limit
        return self

    def limit(self, limit: int) -> 'BaseQuery':
        return self._clone()._limit_func(limit)

    @abstractmethod
    async def all(self):
        pass

    @abstractmethod
    async def first(self):
        pass

    @abstractmethod
    async def get_by_id(self, identifier):
        pass

    @abstractmethod
    async def count(self):
        pass
