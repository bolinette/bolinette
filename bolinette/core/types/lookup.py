from collections.abc import Iterator
from typing import Any, Generic, Protocol, TypeVar, get_origin, override

from bolinette.core.types import Type


class TypeVarMapping(Protocol):
    def __getitem__(self, key: TypeVar, /) -> type[Any]: ...

    def __contains__(self, key: TypeVar, /) -> bool: ...

    def __iter__(self, /) -> Iterator[TypeVar]: ...


class TypeVarLookup[T]:
    __slots__ = ("t", "_lookup")

    def __init__(self, arg: Type[T], /) -> None:
        self.t = arg
        self._lookup = TypeVarLookup.get_lookup(arg)

    @property
    def empty(self) -> bool:
        return len(self._lookup) == 0

    def __getitem__(self, key: TypeVar, /) -> type[Any]:
        if key not in self._lookup:
            raise KeyError(key)
        return self._lookup[key]

    def __contains__(self, key: TypeVar, /) -> bool:
        return key in self._lookup

    def __iter__(self, /) -> Iterator[TypeVar]:
        yield from self._lookup

    def items(self, /) -> Iterator[tuple[TypeVar, type[Any]]]:
        yield from self._lookup.items()

    @override
    def __str__(self) -> str:
        return f"{self.t.base_name}[{", ".join(f"{k}: {v.__qualname__}" for k,v in self._lookup.items())}]"

    @override
    def __repr__(self) -> str:
        return f"<Lookup {self}>"

    @staticmethod
    def get_lookup(t: Type[Any]) -> dict[TypeVar, type[Any]]:
        if not hasattr(t.cls, "__parameters__"):
            return {}
        lookup: dict[TypeVar, type[Any]] = {n: t.vars[i] for i, n in enumerate(t.cls.__parameters__)}
        base_lookups: dict[TypeVar, type[Any]] = {}
        if hasattr(t.cls, "__orig_bases__"):
            for base in t.cls.__orig_bases__:
                if get_origin(base) in (Generic, object):
                    continue
                base_lookups |= TypeVarLookup.get_lookup(Type(base, lookup=lookup))
        return base_lookups | lookup
