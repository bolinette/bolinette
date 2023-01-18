from collections.abc import Callable
from typing import Literal, Protocol, TypeVar, overload

from bolinette import Cache, meta
from bolinette.ext.data import __data_cache__
from bolinette.utils import StringUtils


class Entity(Protocol):
    ...


class EntityMeta:
    def __init__(self, table_name: str, database: str) -> None:
        self.table_name = table_name
        self.database = database


_EntityT = TypeVar("_EntityT", bound=Entity)


def entity(
    *,
    table_name: str | None = None,
    database: str = "default",
    cache: Cache | None = None,
) -> Callable[[type[_EntityT]], type[_EntityT]]:
    def decorator(cls: type[_EntityT]) -> type[_EntityT]:
        meta.set(
            cls,
            EntityMeta(
                table_name if table_name else StringUtils.to_snake_case(cls.__name__),
                database,
            ),
        )
        (cache or __data_cache__).add(EntityMeta, cls)
        return cls

    return decorator


class PrimaryKey:
    @overload
    def __init__(self, columns: list[str]) -> None:
        pass

    @overload
    def __init__(self, *, name: str | None = None) -> None:
        pass

    def __init__(
        self, columns: list[str] | None = None, *, name: str | None = None
    ) -> None:
        self.name = name
        self.columns = columns

    @property
    def __lower_name__(self) -> str:
        return "primary key"


class Unique:
    @overload
    def __init__(self, columns: list[str]) -> None:
        pass

    @overload
    def __init__(self, *, name: str | None = None) -> None:
        pass

    def __init__(
        self, columns: list[str] | None = None, *, name: str | None = None
    ) -> None:
        self.name = name
        self.columns = columns

    @property
    def __lower_name__(self) -> str:
        return "unique constraint"


class ForeignKey:
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


class ManyToOne:
    def __init__(
        self,
        columns: list[str],
        /,
        *,
        lazy: bool | Literal["subquery"] = True,
        other_side: str | None = None,
    ) -> None:
        self.columns = columns
        self.lazy = lazy
        self.other_side = other_side

    @property
    def __lower_name__(self) -> str:
        return "many-to-one relationship"


class OneToMany:
    def __init__(
        self,
        columns: list[str],
        /,
        *,
        other_side: str | None = None,
        lazy: bool | Literal["subquery"] = True,
    ) -> None:
        self.columns = columns
        self.other_side = other_side
        self.lazy = lazy

    @property
    def __lower_name__(self):
        return "one-to-many relationship"


class ManyToMany:
    def __init__(self) -> None:
        super().__init__()

    @property
    def __lower_name__(self):
        return "many-to-many relationship"


class Format:
    def __init__(self, format: Literal["email", "password"], /) -> None:
        self.format = format
