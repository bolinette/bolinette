from abc import abstractmethod, ABC
from typing import Callable, Any, Dict, List, Tuple, Optional

from bolinette import blnt, core
from bolinette.blnt.objects import OrderByParams


class BaseQueryBuilder(ABC):
    def __init__(self, model: 'core.Model', context: 'blnt.BolinetteContext'):
        self.context = context
        self._model = model

    @abstractmethod
    def query(self) -> 'BaseQuery':
        pass

    @abstractmethod
    async def insert_entity(self, values):
        pass

    @abstractmethod
    async def delete_entity(self, entity):
        pass


class BaseQuery(ABC):
    def __init__(self):
        self._filters: Dict[str, Any] = {}
        self._order_by: List[Tuple[Callable[[Any], Any], bool]] = []
        self._offset = 0
        self._limit: Optional[int] = None

    def _base_clone(self, query: 'BaseQuery'):
        query._filters = dict(self._filters)
        query._order_by = list(self._order_by)
        query._limit = self._limit
        query._offset = self._offset

    @abstractmethod
    def _clone(self) -> 'BaseQuery':
        pass

    def _filter_by_func(self, **kwargs) -> 'BaseQuery':
        for key in kwargs:
            self._filters[key] = kwargs[key]
        return self

    def filter_by(self, **kwargs) -> 'BaseQuery':
        return self._clone()._filter_by_func(**kwargs)

    def _order_by_func(self, function: Callable[[Any], Any], *, desc: bool = False) -> 'BaseQuery':
        self._order_by.append((function, desc))
        return self

    def order_by(self, function: Callable[[Any], Any], *, desc: bool = False) -> 'BaseQuery':
        return self._clone()._order_by_func(function, desc=desc)

    @abstractmethod
    def _order_by_from_params(self, params: OrderByParams) -> 'BaseQuery':
        pass

    def order_by_from_params(self, params: OrderByParams) -> 'BaseQuery':
        return self._clone()._order_by_from_params(params)

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
