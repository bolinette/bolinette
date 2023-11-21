from graphlib import CycleError, TopologicalSorter
from typing import Any, Final, Protocol, TypeVar, override

from bolinette.core import Cache, Logger
from bolinette.core.command import Parser
from bolinette.core.environment import CoreSection, Environment, environment
from bolinette.core.exceptions import InitError
from bolinette.core.injection import Injection, injectable
from bolinette.core.injection.injection import InjectionEvent, injection_callback
from bolinette.core.injection.registration import InjectionStrategy
from bolinette.core.mapping import Mapper, type_mapper
from bolinette.core.mapping.mapper import BoolTypeMapper, FloatTypeMapper, IntegerTypeMapper, StringTypeMapper
from bolinette.core.types import Type

ExtT = TypeVar("ExtT", bound="Extension")


class ExtensionModule(Protocol[ExtT]):
    __blnt_ext__: ExtT


class Extension:
    def __init__(self, name: str, dependencies: "list[ExtensionModule[Extension]] | None" = None) -> None:
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
        except CycleError as e:
            raise InitError("A circular dependency was detected in the loaded extensions") from e


class _CoreExtension(Extension):
    def __init__(self) -> None:
        super().__init__("core")

    @override
    def add_cached(self, cache: Cache) -> None:
        environment("core", cache=cache)(CoreSection)

        injection_callback(cache=cache)(InjectionLogger)
        injectable(strategy="singleton", cache=cache)(Injection)
        injectable(strategy="singleton", cache=cache)(Parser)
        injectable(strategy="transient", match_all=True, cache=cache)(Logger)
        injectable(strategy="singleton", cache=cache)(Environment)

        injectable(strategy="singleton", cache=cache)(Mapper)
        type_mapper(int, cache=cache)(IntegerTypeMapper)
        type_mapper(float, cache=cache)(FloatTypeMapper)
        type_mapper(bool, cache=cache)(BoolTypeMapper)
        type_mapper(str, cache=cache)(StringTypeMapper)


core_ext: Final[Extension] = _CoreExtension()


class InjectionLogger:
    def __init__(self, logger: Logger[Injection]) -> None:
        self.logger = logger

    def __call__(self, event: InjectionEvent, type: Type[Any], strategy: InjectionStrategy, instance: Any) -> None:
        match event:
            case "instantiated":
                self.logger.debug(f"Instantiated {type} with strategy '{strategy}'")
