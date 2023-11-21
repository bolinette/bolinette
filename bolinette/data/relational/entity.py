from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import ColumnProperty, DeclarativeBase, InstrumentedAttribute

from bolinette.core import Cache, __user_cache__, meta
from bolinette.data.exceptions import EntityError


class EntityMeta:
    def __init__(self, table_name: str, entity_key: list[InstrumentedAttribute[Any]]) -> None:
        self.table_name = table_name
        self.entity_key = entity_key


def entity[EntityT: DeclarativeBase](
    *,
    entity_key: str | list[str],
    cache: Cache | None = None,
) -> Callable[[type[EntityT]], type[EntityT]]:
    def decorator(cls: type[EntityT]) -> type[EntityT]:
        if not isinstance(entity_key, list):
            _key_names = [entity_key]
        else:
            _key_names = entity_key
        _entity_key: list[InstrumentedAttribute[Any]] = []
        for name in _key_names:
            if not hasattr(cls, name):
                raise EntityError(f"Attribute '{name}' not found", entity=cls)
            attr: InstrumentedAttribute[Any] | Any = getattr(cls, name)
            if (
                not isinstance(attr, InstrumentedAttribute)
                or not hasattr(attr, "prop")
                or not isinstance(attr.prop, ColumnProperty)
            ):
                raise EntityError(f"Attribute '{name}' is not an SQLAlchemy mapped column", entity=cls)
            _entity_key.append(attr)
        meta.set(cls, EntityMeta(cls.__tablename__, _entity_key))
        (cache or __user_cache__).add(EntityMeta, cls)
        return cls

    return decorator
