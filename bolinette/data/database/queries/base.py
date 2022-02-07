from abc import abstractmethod, ABC
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from bolinette import data


T_Entity = TypeVar("T_Entity", bound=data.Entity)


class BaseQueryBuilder(data.WithDataContext, ABC, Generic[T_Entity]):
    def __init__(self, model: "data.Model", data_ctx: data.DataContext):
        data.WithDataContext.__init__(self, data_ctx)
        self._model = model

    @abstractmethod
    def query(self) -> "BaseQuery[T_Entity]":
        pass

    @abstractmethod
    async def insert_entity(self, values) -> T_Entity:
        pass

    @abstractmethod
    async def update_entity(self, entity) -> T_Entity:
        pass

    @abstractmethod
    async def delete_entity(self, entity) -> T_Entity:
        pass


class BaseQuery(ABC, Generic[T_Entity]):
    def __init__(self):
        self._filters_by: dict[str, Any] = {}
        self._filters: list[Callable[[Any], Any]] = []
        self._order_by: list[tuple[str, bool]] = []
        self._offset = 0
        self._limit: int | None = None

    def _base_clone(self, query: "BaseQuery"):
        query._filters_by = dict(self._filters_by)
        query._filters = list(self._filters)
        query._order_by = list(self._order_by)
        query._limit = self._limit
        query._offset = self._offset

    @abstractmethod
    def _clone(self) -> "BaseQuery[T_Entity]":
        pass

    def _filter_by_func(self, **kwargs) -> "BaseQuery[T_Entity]":
        for key in kwargs:
            self._filters_by[key] = kwargs[key]
        return self

    def filter_by(self, **kwargs) -> "BaseQuery[T_Entity]":
        return self._clone()._filter_by_func(**kwargs)

    def _filter_func(self, function: Callable[[Any], Any]):
        self._filters.append(function)
        return self

    def filter(self, function: Callable[[Any], Any]):
        return self._clone()._filter_func(function)

    def _order_by_func(
        self, column: str, *, desc: bool = False
    ) -> "BaseQuery[T_Entity]":
        self._order_by.append((column, desc))
        return self

    def order_by(self, column: str, *, desc: bool = False) -> "BaseQuery[T_Entity]":
        return self._clone()._order_by_func(column, desc=desc)

    def _offset_func(self, offset: int) -> "BaseQuery[T_Entity]":
        self._offset = offset
        return self

    def offset(self, offset: int) -> "BaseQuery[T_Entity]":
        return self._clone()._offset_func(offset)

    def _limit_func(self, limit: int) -> "BaseQuery[T_Entity]":
        self._limit = limit
        return self

    def limit(self, limit: int) -> "BaseQuery[T_Entity]":
        return self._clone()._limit_func(limit)

    @abstractmethod
    async def all(self) -> list[T_Entity]:
        pass

    @abstractmethod
    async def first(self) -> T_Entity:
        pass

    @abstractmethod
    async def get_by_id(self, identifier) -> T_Entity:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass
