from typing import Any, ParamSpec, TypeVar, overload

P = ParamSpec("P")
InstanceT = TypeVar("InstanceT")


class Cache:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._bag: dict[Any, list[Any]] = {}

    def __contains__(self, key: Any) -> bool:
        return key in self._bag

    @overload
    def __getitem__(self, args: tuple[Any, type[InstanceT]], /) -> list[InstanceT]:
        pass

    @overload
    def __getitem__(self, key: Any, /) -> list[Any]:
        pass

    def __getitem__(
        self, args: tuple[Any, type[InstanceT]] | Any, /
    ) -> list[InstanceT] | list[Any]:
        key = None
        match args:
            case (_k, _):
                key = _k
            case _k:
                key = _k
        if key not in self:
            raise KeyError(key)
        return self._bag[key]

    def __delitem__(self, key: Any) -> None:
        if key not in self:
            raise KeyError(key)
        del self._bag[key]

    def init(self, key: Any) -> None:
        self._bag[key] = []

    def add(self, key: Any, value: Any) -> None:
        if key not in self:
            self.init(key)
        self._bag[key].append(value)

    def remove(self, key: Any, value: Any) -> None:
        if key not in self:
            raise KeyError(key)
        self._bag[key] = list(filter(lambda i: i is not value, self._bag[key]))

    @staticmethod
    def _merge(c1: "Cache", c2: "Cache") -> "Cache":
        c3 = Cache()
        for key, values in c1._bag.items():
            for value in values:
                c3.add(key, value)
        for key, values in c2._bag.items():
            for value in values:
                c3.add(key, value)
        return c3

    def __or__(self, __t: Any) -> "Cache":
        if isinstance(__t, Cache):
            return self._merge(self, __t)
        raise NotImplemented

    def __ror__(self, __t: Any) -> "Cache":
        if isinstance(__t, Cache):
            return self._merge(self, __t)
        raise NotImplemented


__core_cache__ = Cache()
__user_cache__ = Cache()
