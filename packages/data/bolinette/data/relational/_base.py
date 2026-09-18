from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar

from escondite import Cache
from sqlalchemy.orm import DeclarativeBase

from bolinette.core import meta


@dataclass(frozen=True, slots=True)
class DeclarativeMeta:
    KEY: ClassVar[str] = "__blnt_data_base_meta__"

    name: str


def get_declarative_bases(cache: Cache, name: str) -> list[type[DeclarativeBase]]:
    bases: list[type[DeclarativeBase]] = []
    for base in cache.get(DeclarativeMeta.KEY, hint=type[DeclarativeBase], raises=False):
        base_meta: DeclarativeMeta = meta.get(base, DeclarativeMeta.KEY)
        if base_meta.name == name:
            bases.append(base)
    return bases


def declarative_base[T: DeclarativeBase](name: str, *, cache: Cache | None = None) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        meta.set(cls, DeclarativeMeta.KEY, DeclarativeMeta(name))
        Cache.with_fallback(cache).add(DeclarativeMeta.KEY, cls)
        return cls

    return decorator
