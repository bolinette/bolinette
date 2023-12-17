from typing import Any


class Cache:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug
        self._bag: dict[Any, list[Any]] = {}

    def __contains__(self, key: Any) -> bool:
        return key in self._bag

    def get[InstanceT](
        self,
        key: Any,
        /,
        *,
        hint: type[InstanceT] | None = None,
        raises: bool = True,
    ) -> list[InstanceT]:
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

    def __or__(self, __t: Any) -> "Cache":
        if isinstance(__t, Cache):
            return self._merge(self, __t)
        return NotImplemented

    def __ror__(self, __t: Any) -> "Cache":
        if isinstance(__t, Cache):
            return self._merge(self, __t)
        return NotImplemented


__user_cache__ = Cache()
