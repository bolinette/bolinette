from collections.abc import Callable
from typing import Any, Literal, overload

from bolinette.core import meta
from bolinette.core.mapping import BolinetteModel


class LoggingConfig(BolinetteModel):
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


class StreamLoggingConfig(LoggingConfig):
    type: Literal["stderr"]
    color: bool = False


class FileLoggingConfig(LoggingConfig):
    type: Literal["file"]
    path: str


class CoreConfigSection(BolinetteModel):
    debug: bool = False
    logging: list[StreamLoggingConfig | FileLoggingConfig] | None = None


class ConfigSectionMeta:
    META_KEY = "__blnt_config_section_meta__"

    def __init__(self, name: str) -> None:
        self.name = name


class ConfigSection[T: BolinetteModel]:
    def __init__(self, type: type[T], name: str, value: T) -> None:
        self.type = type
        self.name = name
        self.value = value


def _set_env_meta(cls: type[Any], name: str) -> None:
    meta.set(cls, ConfigSectionMeta.META_KEY, ConfigSectionMeta(name))


@overload
def config_section[EnvT](cls: type[EnvT], name: str, /) -> type[EnvT]: ...
@overload
def config_section[EnvT](name: str, /) -> Callable[[type[EnvT]], type[EnvT]]: ...
def config_section(*args: Any) -> Any:
    match args:
        case (str() as name,):

            def decorator(cls: type[Any]) -> type[Any]:
                _set_env_meta(cls, name)
                return cls

            return decorator
        case (cls, str() as name):
            _set_env_meta(cls, name)
            return cls
        case _:
            raise TypeError()
