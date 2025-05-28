from typing import TYPE_CHECKING

from bolinette.core import Cache, CoreSection, command, startup
from bolinette.core.command import Parser
from bolinette.core.command.commands.debug import debug_injection_command
from bolinette.core.command.commands.new_project import new_project, register_new_project_hooks
from bolinette.core.environment import Environment, environment
from bolinette.core.environment.resolver import EnvironmentSectionResolver
from bolinette.core.events import EventDispatcher
from bolinette.core.extensions import Extension, ExtensionModule
from bolinette.core.injection import Injection, injectable, injection_arg_resolver
from bolinette.core.logging import LoggerArgResolver
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

if TYPE_CHECKING:
    from jinja2 import BaseLoader


class CoreExtension:
    def __init__(self, cache: Cache) -> None:
        self.cache = cache
        self.name: str = "core"
        self.dependencies: list[ExtensionModule[Extension]] = []

        environment("core", cache=cache)(CoreSection)

        injectable(strategy="singleton", cache=cache)(Injection)
        injectable(strategy="singleton", cache=cache)(Parser)
        injectable(strategy="singleton", cache=cache)(Environment)
        injectable(strategy="singleton", cache=cache)(EventDispatcher)

        injection_arg_resolver()(LoggerArgResolver)
        injection_arg_resolver()(EnvironmentSectionResolver)

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
        command(
            "new project",
            "Create a new Bolinette project",
            cache=cache,
            run_startup=False,
        )(new_project)
        register_new_project_hooks(cache)

    def use_jinja_templating(self, loader: "BaseLoader | None" = None) -> "CoreExtension":
        from bolinette.core.templating.jinja import JinjaResolver

        async def register_config(inject: Injection) -> None:
            from bolinette.core.templating.jinja import JinjaConfig

            inject.add_singleton(JinjaConfig, instance=JinjaConfig(loader=loader))

        injection_arg_resolver(cache=self.cache)(JinjaResolver)
        startup(cache=self.cache)(register_config)
        return self
