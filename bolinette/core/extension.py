from graphlib import CycleError, TopologicalSorter
from typing import Final, Protocol

from bolinette.core import Cache, CoreSection, command
from bolinette.core.command import Parser, debug_injection_command
from bolinette.core.environment import Environment, environment
from bolinette.core.events import EventDispatcher
from bolinette.core.exceptions import InitError
from bolinette.core.injection import Injection, injectable, injection_arg_resolver
from bolinette.core.injection.injection import InjectionEvent, injection_callback
from bolinette.core.logging import Logger, LoggerArgResolver
from bolinette.core.mapping import Mapper, mapping_worker
from bolinette.core.mapping.mapper import (
    BoolMapper,
    BytesMapper,
    DictMapper,
    FloatMapper,
    IntegerMapper,
    LiteralMapper,
    SequenceMapper,
    StringMapper,
)
from bolinette.core.types.checker import (
    DefaultTypeChecker,
    LiteralTypeChecker,
    ProtocolTypeChecker,
    TypeChecker,
    TypedDictChecker,
    type_checker,
)


class ExtensionModule[ExtT: "Extension"](Protocol):
    __blnt_ext__: Final[type[ExtT]]


class Extension(Protocol):
    name: str
    dependencies: "list[ExtensionModule[Extension]]"

    def __init__(self, cache: Cache) -> None: ...


def sort_extensions(extensions: list[Extension]) -> list[Extension]:
    sorter: TopologicalSorter[type[Extension]] = TopologicalSorter()
    for ext in extensions:
        sorter.add(type(ext), *[m.__blnt_ext__ for m in ext.dependencies])
    try:
        ordered_types = list(sorter.static_order())
        instance_map = {type(ext): ext for ext in extensions}
        return [instance_map[t] for t in ordered_types]
    except CycleError as e:
        raise InitError("A circular dependency was detected in the loaded extensions") from e


class CoreExtension:
    def __init__(self, cache: Cache) -> None:
        self.name = "core"
        self.dependencies: list[ExtensionModule[Extension]] = []

        environment("core", cache=cache)(CoreSection)

        injection_callback(cache=cache)(InjectionLogger)
        injectable(strategy="singleton", cache=cache)(Injection)
        injectable(strategy="singleton", cache=cache)(Parser)
        injectable(strategy="singleton", cache=cache)(Environment)
        injectable(strategy="singleton", cache=cache)(EventDispatcher)

        injection_arg_resolver()(LoggerArgResolver)

        injectable(strategy="singleton", cache=cache)(TypeChecker)
        type_checker(priority=-700, cache=cache)(ProtocolTypeChecker)
        type_checker(priority=-800, cache=cache)(TypedDictChecker)
        type_checker(priority=-900, cache=cache)(LiteralTypeChecker)
        type_checker(priority=-1000, cache=cache)(DefaultTypeChecker)

        injectable(strategy="singleton", cache=cache)(Mapper)
        mapping_worker(cache=cache)(IntegerMapper)
        mapping_worker(cache=cache)(FloatMapper)
        mapping_worker(cache=cache)(BoolMapper)
        mapping_worker(cache=cache)(StringMapper)
        mapping_worker(cache=cache)(BytesMapper)
        mapping_worker(cache=cache, match_all=True)(LiteralMapper)
        mapping_worker(cache=cache, match_all=True)(DictMapper)
        mapping_worker(cache=cache, match_all=True)(SequenceMapper)

        command(
            "debug injection",
            "Debug command that lists all registered types",
            cache=cache,
            run_startup=False,
        )(debug_injection_command)


class InjectionLogger:
    def __init__(self, logger: Logger[Injection]) -> None:
        self.logger = logger

    def __call__(self, event: InjectionEvent) -> None:
        match event["event"]:
            case "instantiated":
                self.logger.debug(f"Instantiated {event['type']} with strategy '{event['strategy']}'")
            case "session_open":
                self.logger.debug("Scoped session open")
            case "session_closed":
                self.logger.debug("Scoped session closed")
            case "async_session_open":
                self.logger.debug("Async scoped session open")
            case "async_session_closed":
                self.logger.debug("Async scoped session closed")
