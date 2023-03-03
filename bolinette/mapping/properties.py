from abc import ABC
from typing import Any, Callable, Concatenate, Generic, ParamSpec, TypeVar, get_type_hints

from bolinette.exceptions import InitError

PropParams = ParamSpec("PropParams")
ReturnT = TypeVar("ReturnT")


class _MappingProp(Generic[ReturnT], ABC):
    def __init__(
        self,
        origin: str,
        mappingType: type[Any],
    ) -> None:
        self.origin = origin
        self.mappingType = mappingType

    def __get__(self, _, cls: type[Any]) -> ReturnT:
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{self.origin}'")


class _MapFrom(Generic[ReturnT], _MappingProp[ReturnT]):
    def __init__(
        self,
        origin: str,
        mappingType: type[Any],
        func: Callable[Concatenate[Any, PropParams], ReturnT],
    ) -> None:
        super().__init__(origin, mappingType)
        self.func = func


class _MapTo(Generic[ReturnT], _MappingProp[ReturnT]):
    def __init__(
        self,
        origin: str,
        mappingType: type[Any],
        func: Callable[Concatenate[Any, PropParams], ReturnT],
    ) -> None:
        super().__init__(origin, mappingType)
        self.func = func


def mapFrom(func: Callable[Concatenate[Any, PropParams], ReturnT]) -> _MappingProp[ReturnT]:
    hints = get_type_hints(func)
    if "return" not in hints:
        raise InitError(
            f"Property '{func.__name__}' must specify a return type hint when decorated by @{mapFrom.__name__}"
        )
    return _MapFrom(func.__name__, hints["return"], func)


def mapTo(func: Callable[Concatenate[Any, PropParams], ReturnT]) -> _MappingProp[ReturnT]:
    hints = get_type_hints(func)
    if "return" not in hints:
        raise InitError(
            f"Property '{func.__name__}' must specify a return type hint when decorated by @{mapTo.__name__}"
        )
    return _MapTo(func.__name__, hints["return"], func)
