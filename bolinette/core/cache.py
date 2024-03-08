from typing import Any, overload, override


class Cache:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._bag: dict[Any, list[Any]] = {}

    @overload
    def get(self, key: Any, /, *, raises: bool = True) -> list[Any]: ...

    @overload
    def get[InstanceT](self, key: Any, /, *, hint: type[InstanceT], raises: bool = True) -> list[InstanceT]: ...

    def get(
        self,
        key: Any,
        /,
        *,
        hint: Any | None = None,
        raises: bool = True,
    ) -> list[Any]:
        if key not in self:
            if raises:
                raise KeyError(key)
            return []
        return self._bag[key]

    def delete(self, key: Any) -> None:
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

    def __contains__(self, key: Any) -> bool:
        return key in self._bag

    def __or__(self, other: "Cache", /) -> "Cache":
        return self._merge(self, other)

    def __ror__(self, other: "Cache", /) -> "Cache":
        return self._merge(self, other)

    @override
    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, Cache):
            return NotImplemented
        if len(self._bag) != len(other._bag):
            return False
        for key, self_bag in self._bag.items():
            if key not in other._bag:
                return False
            other_bag = other._bag[key]
            for self_value, other_value in zip(self_bag, other_bag, strict=True):
                if self_value != other_value:
                    return False
        return True


__user_cache__ = Cache()
