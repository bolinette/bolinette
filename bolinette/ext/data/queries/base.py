from abc import ABC, abstractmethod
from collections.abc import AsyncIterable
from typing import Any, Generic, Self, TypeVar, Callable

from bolinette.ext.data import Entity

EntityT = TypeVar("EntityT", bound=Entity)


QueryT = TypeVar("QueryT", bound="BaseQuery")


class BaseQuery(ABC, Generic[EntityT]):
    @abstractmethod
    def where(self, function: Callable[[EntityT], bool]) -> Self:
        ...

    @abstractmethod
    def order_by(self, column: str, *, desc: bool = False) -> Self:
        ...

    @abstractmethod
    def offset(self, offset: int) -> Self:
        ...

    @abstractmethod
    def limit(self, limit: int) -> Self:
        ...

    @abstractmethod
    def include(self, function: Callable[[EntityT], Any]) -> Self:
        ...

    @abstractmethod
    def all(self) -> AsyncIterable[EntityT]:
        ...
