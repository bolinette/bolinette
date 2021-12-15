from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Generic, TypeVar, Any, overload

from bolinette import abc


class Injectable(ABC):
    def __init__(self, **kwargs) -> None: ...


class Instantiable(ABC):
    def __init__(self, **kwargs) -> None: ...


T_Instance = TypeVar('T_Instance')
T_Instantiable = TypeVar('T_Instantiable', bound=Instantiable)
T_Injectable = TypeVar('T_Injectable', bound=Injectable)
T_WContext = TypeVar('T_WContext', bound=abc.WithContext)


class Injection(abc.WithContext, ABC):
    def __init__(self, context: abc.Context) -> None:
        super().__init__(context)

    @abstractmethod
    def register(self, _type: type[abc.WithContext], collection: str, name: str, *,
                 func: Callable[[T_WContext], None] | None = None,
                 params: dict[str, Any] = None) -> None: ...

    @overload
    def require(self, _type: type[T_WContext], *, immediate: bool = False) -> T_WContext: ...
    @overload
    def require(self, collection: str, name: str, *, immediate: bool = False) -> Any: ...

    @abstractmethod
    def require(self, *args, **kwargs) -> Any: ...

    @overload
    def registered(self) -> Iterable[type]: ...
    @overload
    def registered(self, *, of_type: type[T_WContext]) -> Iterable[type[T_WContext]]: ...
    @overload
    def registered(self, *, get_strings: bool) -> Iterable[tuple[str, str]]: ...

    @abstractmethod
    def registered(self, *args, **kwargs): ...

    @abstractmethod
    def collect_types(self, _type: type[T_Injectable]) -> Iterable[type[T_Injectable]]: ...

    @abstractmethod
    def collect_type(self, collection: str, name: str) -> type[Injectable]: ...

    @abstractmethod
    def get_global_instances(self, _type: type[T_Instance]) -> Iterable[T_Instance]: ...
