from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Generic, TypeVar, Any, overload

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
    def register(self, _type: type[T_Inject], collection: str, name: str, *,
                 func: Callable[[T_Inject], None] | None = None,
                 params: dict[str, Any] = None) -> None: ...

    @overload
    def require(self, _type: type[T_Inject], *, immediate: bool = False) -> T_Inject: ...
    @overload
    def require(self, collection: str, name: str, *, immediate: bool = False) -> Any: ...

    @abstractmethod
    def require(self, *args, **kwargs) -> Any: ...

    @overload
    def registered(self) -> Iterable[type]: ...
    @overload
    def registered(self, *, of_type: type[T_Inject]) -> Iterable[type[T_Inject]]: ...
    @overload
    def registered(self, *, get_strings: bool = True) -> Iterable[tuple[str, str]]: ...

    @abstractmethod
    def registered(self, *args, **kwargs): ...
