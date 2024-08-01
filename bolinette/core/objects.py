from dataclasses import dataclass
from typing import Literal


@dataclass(init=False)
class LoggingConfig:
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


@dataclass(init=False)
class StreamLoggingConfig(LoggingConfig):
    type: Literal["stderr"]
    color: bool = False


@dataclass(init=False)
class FileLoggingConfig(LoggingConfig):
    type: Literal["file"]
    path: str


class CoreSection:
    debug: bool = False
    logging: list[StreamLoggingConfig | FileLoggingConfig] | None = None
