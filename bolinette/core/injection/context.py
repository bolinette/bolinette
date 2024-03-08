from collections.abc import Iterable
from typing import Any, Literal, overload

from bolinette.core.types import Type


class InjectionContext:
    __slots__ = ("_instances",)

    def __init__(self) -> None:
        self._instances: dict[Type[Any], Any] = {}

    def has_instance(self, t: Type[Any]) -> bool:
        return t in self._instances

    def set_instance[InstanceT](self, t: Type[InstanceT], instance: InstanceT) -> None:
        self._instances[t] = instance

    def get_instance[InstanceT](self, t: Type[InstanceT]) -> InstanceT:
        return self._instances[t]

    @overload
    def get_instances(self) -> Iterable[Any]: ...

    @overload
    def get_instances(self, *, with_types: Literal[True]) -> Iterable[tuple[type[Any], Any]]: ...

    def get_instances(self, **kwargs: Any) -> Iterable[tuple[type[Any], Any]] | Iterable[Any]:
        if "with_types" in kwargs:
            return [(t, i) for t, i in self._instances.items()]
        return [i for i in self._instances.values()]
