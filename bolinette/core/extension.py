from graphlib import CycleError, TopologicalSorter
from typing import Protocol

from typing_extensions import override

from bolinette.core import Cache, Logger, environment
from bolinette.core.command import Parser
from bolinette.core.environment import CoreSection
from bolinette.core.exceptions import InitError
from bolinette.core.injection import Injection, injectable
from bolinette.core.mapping import Mapper, type_mapper
from bolinette.core.mapping.mapper import BoolTypeMapper, FloatTypeMapper, IntegerTypeMapper, StringTypeMapper
from bolinette.core.utils import FileUtils, PathUtils


class _ExtensionModule(Protocol):
    __blnt_ext__: "Extension"


class Extension:
    def __init__(self, name: str, dependencies: "list[_ExtensionModule] | None" = None) -> None:
        self.name = name
        self.dependencies = [m.__blnt_ext__ for m in dependencies] if dependencies else []

    def add_cached(self, cache: Cache) -> None:
        pass

    @staticmethod
    def sort_extensions(extensions: "list[Extension]") -> "list[Extension]":
        sorter: TopologicalSorter[Extension] = TopologicalSorter()
        for ext in extensions:
            sorter.add(ext, *ext.dependencies)
        try:
            return list(sorter.static_order())
        except CycleError:
            raise InitError("A circular dependency was detected in the loaded extensions")


class _CoreExtension(Extension):
    def __init__(self) -> None:
        super().__init__("core")

    @override
    def add_cached(self, cache: Cache) -> None:
        environment("core", cache=cache)(CoreSection)

        injectable(strategy="singleton", cache=cache)(Injection)
        injectable(strategy="singleton", cache=cache)(Parser)
        injectable(strategy="singleton", cache=cache)(Mapper)
        injectable(strategy="transcient", match_all=True, cache=cache)(Logger)
        injectable(strategy="singleton", cache=cache)(PathUtils)
        injectable(strategy="singleton", cache=cache)(FileUtils)

        type_mapper(int, cache=cache)(IntegerTypeMapper)
        type_mapper(float, cache=cache)(FloatTypeMapper)
        type_mapper(bool, cache=cache)(BoolTypeMapper)
        type_mapper(str, cache=cache)(StringTypeMapper)


core_ext = _CoreExtension()
