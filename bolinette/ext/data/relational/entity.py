from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import DeclarativeBase

from bolinette import Cache, meta
from bolinette.ext.data import __data_cache__
from bolinette.utils import StringUtils


class EntityMeta:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name


EntityT = TypeVar("EntityT", bound=DeclarativeBase)


def entity(
    *,
    table_name: str | None = None,
    cache: Cache | None = None,
) -> Callable[[type[EntityT]], type[EntityT]]:
    def decorator(cls: type[EntityT]) -> type[EntityT]:
        _table_name = table_name if table_name else StringUtils.to_snake_case(cls.__name__)
        meta.set(cls, EntityMeta(_table_name))
        (cache or __data_cache__).add(EntityMeta, cls)
        return cls

    return decorator
