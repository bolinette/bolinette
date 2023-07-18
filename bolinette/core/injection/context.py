from typing import Any, TypeVar

from bolinette.core.types import Type

InstanceT = TypeVar("InstanceT")


class InjectionContext:
    __slots__ = ("_instances",)

    def __init__(self) -> None:
        self._instances: dict[int, Any] = {}

    def has_instance(self, t: Type[Any]) -> bool:
        return hash(t) in self._instances

    def set_instance(self, t: Type[InstanceT], instance: InstanceT) -> None:
        self._instances[hash(t)] = instance

    def get_instance(self, t: Type[InstanceT]) -> InstanceT:
        return self._instances[hash(t)]
