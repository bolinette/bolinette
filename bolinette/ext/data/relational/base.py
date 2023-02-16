from sqlalchemy.orm import DeclarativeBase

from bolinette import Cache, meta
from bolinette.ext.data import __data_cache__
from bolinette.utils import StringUtils


def get_base(name: str, *, cache: Cache | None = None) -> type[DeclarativeBase]:
    cache = cache or __data_cache__
    if DeclarativeMeta not in cache:
        cache.init(DeclarativeMeta)
    bases = cache.get(DeclarativeMeta, hint=type[DeclarativeBase])
    for base in bases:
        _m = meta.get(base, DeclarativeMeta)
        if _m.name == name:
            return base
    base = type(f"{StringUtils.capitalize(name)}Database", (DeclarativeBase,), {})
    meta.set(base, DeclarativeMeta(name))
    cache.add(DeclarativeMeta, base)
    return base


class DeclarativeMeta:
    def __init__(self, name: str) -> None:
        self.name = name
