from collections.abc import Callable

from sqlalchemy.orm import DeclarativeBase

from bolinette.core import Cache, __user_cache__, meta


class EntityMeta:
    def __init__(self, table_name: str) -> None:
        self.table_name = table_name


def entity[EntityT: DeclarativeBase](*, cache: Cache | None = None) -> Callable[[type[EntityT]], type[EntityT]]:
    def decorator(cls: type[EntityT]) -> type[EntityT]:
        meta.set(cls, EntityMeta(cls.__tablename__))
        (cache or __user_cache__).add(EntityMeta, cls)
        return cls

    return decorator
