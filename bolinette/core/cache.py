from collections.abc import Iterable
from typing import Any, overload

from bolinette.core import abc
from bolinette.exceptions import InitError


class BolinetteCache:
    def __init__(self):
        self._all_types: set[type[Any]] = set()
        self._types_by_name: dict[str, dict[str, type[Any]]] = {}
        self._all_instances: list[Any] = []
        self._instances_by_name: dict[str, dict[str, Any]] = {}

    def _push_type(self, _type: type[Any], collection: str, name: str):
        if collection not in self._types_by_name:
            self._types_by_name[collection] = {}
        if name in self._types_by_name[collection]:
            self._all_types.remove(self._types_by_name[collection][name])
        self._all_types.add(_type)
        self._types_by_name[collection][name] = _type

    def _push_instance(self, instance: Any, collection: str, name: str):
        if collection not in self._instances_by_name:
            self._instances_by_name[collection] = {}
        self._instances_by_name[collection][name] = instance
        self._all_instances.append(instance)

    @overload
    def push(self, _type: type[Any], collection: str, name: str) -> None:
        ...

    @overload
    def push(self, instance: Any, collection: str, name: str) -> None:
        ...

    def push(self, param: type[Any] | Any, collection: str, name: str):
        if isinstance(param, type):
            return self._push_type(param, collection, name)
        return self._push_instance(param, collection, name)

    def collect_by_type(
        self, _type: type[abc.T_Instance]
    ) -> Iterable[type[abc.T_Instance]]:
        return (t for t in self._all_types if issubclass(t, _type))

    def collect_by_name(self, collection: str, name: str) -> type[Any]:
        if (
            collection not in self._types_by_name
            or name not in self._types_by_name[collection]
        ):
            raise InitError(f"{collection}.{name} does not exist in registered types")
        return self._types_by_name[collection][name]

    def get_instances(self, _type: type[abc.T_Instance]) -> Iterable[abc.T_Instance]:
        return (i for i in self._all_instances if isinstance(i, _type))


__global_cache__ = BolinetteCache()
