from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import DeclarativeBase

from bolinette import Cache, meta
from bolinette.ext.data import __data_cache__


class EntityMeta:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name


EntityT = TypeVar("EntityT", bound=DeclarativeBase)


def entity(
    *,
    cache: Cache | None = None,
) -> Callable[[type[EntityT]], type[EntityT]]:
    def decorator(cls: type[EntityT]) -> type[EntityT]:
        meta.set(cls, EntityMeta(cls.__tablename__))
        (cache or __data_cache__).add(EntityMeta, cls)
        return cls

    return decorator
