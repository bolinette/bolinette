from collections.abc import Callable, Sequence
from pathlib import Path
from typing import override

from escondite import Cache
from soupape import ServiceCollection, injectable

from bolinette.core._logging import resolve_logger
from bolinette.core.commands import CommandParser, CommandRunner, command
from bolinette.core.commands._bundled import (
    create_app_file,
    create_dunder_init,
    create_env_files,
    create_gitignore,
    debug_injection_command,
    new_project,
    update_pyproject_toml,
)
from bolinette.core.configuration import (
    Configuration,
    ConfigurationOptions,
    CoreConfigSection,
    config_section,
    resolve_config_section,
)
from bolinette.core.events import EventDispatcher
from bolinette.core.extensions import Extension, NewProjectHook
from bolinette.core.mapping import (
    DataclassProtocol,
    Mapper,
    MappingProtocol,
    PlainObjectProtocol,
    PydanticProtocol,
    SequenceProtocol,
    SetProtocol,
    TypedDictProtocol,
    mapping_protocol,
)


def _make_cache_resolver(cache: Cache) -> Callable[[], Cache]:
    def _resolve_cache() -> Cache:
        return cache

    return _resolve_cache


def _make_instance_resolver[T](interface: type[T], instance: T) -> Callable[[], T]:
    def _resolve() -> T:
        return instance

    _resolve.__annotations__ = {"return": interface}
    return _resolve


class CoreExtension(Extension):
    name = "core"

    def __init__(self, *, env_folder: Path | str | None = None) -> None:
        self._options = ConfigurationOptions(env_folder=None if env_folder is None else Path(env_folder))

    @override
    def get_new_project_hooks(self) -> Sequence[NewProjectHook]:
        return (create_dunder_init, create_app_file, update_pyproject_toml, create_env_files, create_gitignore)

    @override
    def register_services(self, services: ServiceCollection, cache: Cache) -> None:
        from bolinette.core import Bolinette

        config_section(CoreConfigSection, "core")

        injectable.singleton(_make_cache_resolver(cache), cache=cache)
        injectable.singleton(_make_instance_resolver(ConfigurationOptions, self._options), cache=cache)
        injectable.singleton(Configuration, cache=cache)
        injectable.singleton(resolve_config_section, cache=cache)
        injectable.singleton(EventDispatcher, cache=cache)
        injectable.singleton(resolve_logger, cache=cache)
        injectable.singleton(CommandParser, cache=cache)
        injectable.singleton(CommandRunner, cache=cache)
        injectable.singleton(Bolinette, cache=cache)

        injectable.singleton(Mapper, cache=cache)
        mapping_protocol(PydanticProtocol, cache=cache)
        mapping_protocol(TypedDictProtocol, cache=cache)
        mapping_protocol(DataclassProtocol, cache=cache)
        mapping_protocol(MappingProtocol, cache=cache)
        mapping_protocol(SequenceProtocol, cache=cache)
        mapping_protocol(SetProtocol, cache=cache)
        mapping_protocol(PlainObjectProtocol, cache=cache)

        command(
            debug_injection_command,
            "debug injection",
            "Prints all registered types in the service collection",
            cache=cache,
        )
        command(
            new_project,
            "new project",
            "Create a new Bolinette project",
            cache=cache,
            run_startup=False,
        )
