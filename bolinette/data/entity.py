from abc import ABC, abstractmethod
from typing import Literal, Protocol, TypeVar, overload

from bolinette.core import Cache, meta
from bolinette.core.utils import StringUtils
from bolinette.data import __data_cache__


class Entity(Protocol):
    def __init__(self) -> None:
        pass


class EntityMeta:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name


_EntityT = TypeVar("_EntityT", bound=Entity)


class _EntityDecorator:
    def __call__(self, *, table_name: str | None = None, cache: Cache | None = None):
        def decorator(cls: type[_EntityT]) -> type[_EntityT]:
            meta.set(
                cls,
                EntityMeta(
                    table_name
                    if table_name
                    else StringUtils.to_snake_case(cls.__name__)
                ),
            )
            (cache or __data_cache__).add(EntityMeta, cls)
            return cls

        return decorator


entity = _EntityDecorator()


class _Constraint(ABC):
    @property
    @abstractmethod
    def __lower_name__(self) -> str:
        pass


class PrimaryKey(_Constraint):
    @overload
    def __init__(self, columns: list[str]):
        pass

    @overload
    def __init__(self, *, name: str | None = None):
        pass

    def __init__(
        self, columns: list[str] | None = None, *, name: str | None = None
    ) -> None:
        self.name = name
        self.columns = columns

    @property
    def __lower_name__(self) -> str:
        return "primary key"


class Unique(_Constraint):
    @overload
    def __init__(self, columns: list[str]):
        pass

    @overload
    def __init__(self, *, name: str | None = None):
        pass

    def __init__(
        self, columns: list[str] | None = None, *, name: str | None = None
    ) -> None:
        self.name = name
        self.columns = columns

    @property
    def __lower_name__(self) -> str:
        return "unique constraint"


class ForeignKey(_Constraint):
    def __init__(
        self,
        target: type[_EntityT],
        columns: list[str] | None = None,
        *,
        name: str | None = None,
    ) -> None:
        self.target = target
        self.name = name
        self.columns = columns

    @property
    def __lower_name__(self) -> str:
        return "foreign key"


class ManyToOne(_Constraint):
    def __init__(self, column: list[str], target: type[Entity] | None = None, /) -> None:
        self.column = column
        self.target = target

    @property
    def __lower_name__(self) -> str:
        return "many-to-one constraint"


class Format:
    def __init__(self, format: Literal["email", "password"], /) -> None:
        self.format = format
