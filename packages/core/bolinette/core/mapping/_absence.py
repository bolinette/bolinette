from enum import Enum, auto
from typing import Final, Self, TypeGuard


class _Absent:
    __slots__ = ()
    _instance: "_Absent | None" = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance  # pyright: ignore[reportReturnType]

    def __repr__(self) -> str:
        return "ABSENT"

    def __bool__(self) -> bool:
        return False


ABSENT: Final[_Absent] = _Absent()

type Maybe[T] = T | _Absent


def is_present[T](value: Maybe[T]) -> TypeGuard[T]:
    return value is not ABSENT


class Generation(Enum):
    NONE = auto()

    CLIENT_DEFAULT = auto()

    SERVER_GENERATED = auto()


class MapMode(Enum):
    CREATE = auto()

    MERGE = auto()
