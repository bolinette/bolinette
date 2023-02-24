from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import DeclarativeBase

from bolinette import Cache, __user_cache__, meta


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
        (cache or __user_cache__).add(EntityMeta, cls)
        return cls

    return decorator
