from collections.abc import Iterator
from typing import Any, Generic, TypeVar, get_origin

from bolinette.core.types import Type


class TypeVarLookup[T]:
    __slots__ = ("t", "_lookup")

    def __init__(self, t: Type[T]) -> None:
        self.t = t
        self._lookup = TypeVarLookup.get_lookup(t)

    @property
    def empty(self) -> bool:
        return self._lookup is None or len(self._lookup) == 0

    def __getitem__(self, key: TypeVar) -> type[Any]:
        if self._lookup is None or key not in self._lookup:
            raise KeyError(key)
        return self._lookup[key]

    def __contains__(self, key: TypeVar) -> bool:
        return self._lookup is not None and key in self._lookup

    def __iter__(self) -> Iterator[tuple[TypeVar, type]]:
        if self._lookup is None:
            return iter(())
        return ((t, v) for t, v in self._lookup.items())

    @staticmethod
    def get_lookup(t: Type[Any]) -> dict[TypeVar, type[Any]] | None:
        if not hasattr(t.cls, "__parameters__"):
            return None
        lookup: dict[TypeVar, type[Any]] = {}
        if hasattr(t.cls, "__orig_bases__"):
            for base in t.cls.__orig_bases__:
                if get_origin(base) is Generic:
                    continue
                if (base_lookup := TypeVarLookup.get_lookup(Type(base))) is not None:
                    lookup |= base_lookup
        return lookup | {n: t.vars[i] for i, n in enumerate(t.cls.__parameters__)}
