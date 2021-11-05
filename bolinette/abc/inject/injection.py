from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Any

from bolinette import abc


class Instantiable(ABC):
    def __init__(self, **kwargs) -> None:
        pass


T_Instantiable = TypeVar('T_Instantiable', bound=Instantiable)
T_Inject = TypeVar('T_Inject', bound=abc.WithContext)


class Collection(abc.WithContext, ABC, Generic[T_Inject]):
    def __init__(self, context: abc.Context) -> None:
        super().__init__(context)


class Injection(abc.WithContext, ABC):
    def __init__(self, context: abc.Context) -> None:
        super().__init__(context)

    @abstractmethod
    def __add_collection__(self, name: str, _type: type[Any]):
        pass

    @abstractmethod
    def __get_collection__(self, name: str) -> Collection[Any]:
        pass
