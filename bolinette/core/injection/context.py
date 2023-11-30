from collections.abc import Iterable
from typing import Any

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

    @property
    def instances(self) -> Iterable[tuple[Type[Any], Any]]:
        return ((t, i) for t, i in self._instances.items())
