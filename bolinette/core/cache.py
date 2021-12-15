from collections.abc import Iterable
from typing import Any

from bolinette import abc
from bolinette.core.commands import Command
from bolinette.exceptions import InitError


class BolinetteCache:
    def __init__(self):
        self._all_types: set[type[abc.inject.Injectable]] = set()
        self._types_by_name: dict[str, dict[str, type[abc.inject.Injectable]]] = {}
        self._all_instances: list[Any] = []
        self._instances_by_name: dict[str, dict[str, Any]] = {}

    def register(self, _type: type, collection: str, name: str):
        if not issubclass(_type, abc.inject.Injectable):
            raise InitError(f'Type {_type} has to be an injectable class')
        if collection not in self._types_by_name:
            self._types_by_name[collection] = {}
        if name in self._types_by_name[collection]:
            self._all_types.remove(self._types_by_name[collection][name])
        self._all_types.add(_type)
        self._types_by_name[collection][name] = _type

    def register_instance(self, instance: Any, collection: str, name: str):
        if collection not in self._instances_by_name:
            self._instances_by_name[collection] = {}
        self._instances_by_name[collection][name] = instance
        self._all_instances.append(instance)

    def collect_by_type(self, _type: type[abc.inject.Injectable]) -> Iterable[type[abc.inject.Injectable]]:
        return (t for t in self._all_types if issubclass(t, _type))

    def collect_by_name(self, collection: str, name: str) -> type[abc.inject.Injectable]:
        if collection not in self._types_by_name or name not in self._types_by_name[collection]:
            raise InitError(f'{collection}.{name} does not exist in registered types')
        return self._types_by_name[collection][name]

    def get_instances(self, _type: type[abc.inject.T_Instance]) -> Iterable[abc.inject.T_Instance]:
        return (i for i in self._all_instances if isinstance(i, _type))


cache = BolinetteCache()
