from sqlalchemy.orm import DeclarativeBase

from bolinette.core import Cache, __user_cache__, meta
from bolinette.core.utils import StringUtils


def get_base(name: str, *, cache: Cache | None = None) -> type[DeclarativeBase]:
    cache = cache or __user_cache__
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
