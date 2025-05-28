from dataclasses import dataclass
from typing import Literal


@dataclass
class LoggingConfig:
    level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]


@dataclass
class StreamLoggingConfig(LoggingConfig):
    type: Literal["stderr"]
    color: bool = False


@dataclass
class FileLoggingConfig(LoggingConfig):
    type: Literal["file"]
    path: str


@dataclass
class CoreSection:
    debug: bool = False
    logging: list[StreamLoggingConfig | FileLoggingConfig] | None = None
