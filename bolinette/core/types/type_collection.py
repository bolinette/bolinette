from typing import Any

from bolinette.core.types.type import Type


class TypeContainer[K, V]:
    def __init__(self, t: type[K]) -> None:
        self.cls = t
        self.match_all: V | None = None
        self.values: dict[int, V] = {}

    def has_type(self, t: Type[K]) -> bool:
        return hash(t) in self.values

    def has_match_all(self) -> bool:
        return self.match_all is not None

    def is_registered(self, t: Type[K]) -> bool:
        return self.has_type(t) or self.has_match_all()

    def add(self, t: Type[K], v: V, /) -> None:
        self.values[hash(t)] = v

    def set_match_all(self, t: Type[K], v: V, /) -> None:
        self.match_all = v

    def get(self, t: Type[K]) -> V:
        if (h := hash(t)) in self.values:
            return self.values[h]
        if self.match_all is not None:
            return self.match_all
        raise KeyError(t)


class TypeCollection[V]:
    def __init__(self) -> None:
        self._containers: dict[type[Any], TypeContainer[Any, V]] = {}

    def add(self, t: Type[Any], v: V, /, *, match_all: bool = False) -> None:
        if (_cls := t.cls) not in self._containers:
            self._containers[_cls] = TypeContainer(_cls)
        if match_all:
            self._containers[_cls].set_match_all(t, v)
        else:
            self._containers[_cls].add(t, v)

    def has(self, t: Type[Any]) -> bool:
        return t.cls in self._containers

    def get(self, t: Type[Any]) -> V:
        if (h := t.cls) in self._containers:
            return self._containers[h].get(t)
        raise KeyError(t)
