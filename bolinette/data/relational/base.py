from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import DeclarativeBase

from bolinette.core import Cache, __user_cache__, meta


@dataclass
class DeclarativeMeta:
    name: str


def declarative_base[T: DeclarativeBase](name: str, *, cache: Cache | None = None) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        meta.set(cls, DeclarativeMeta(name))
        (cache or __user_cache__).add(DeclarativeMeta, cls)
        return cls

    return decorator
