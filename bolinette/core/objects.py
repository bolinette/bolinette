from dataclasses import dataclass
from typing import Literal


@dataclass(init=False)
class StreamLoggingConfig:
    type: Literal["stderr"]


@dataclass(init=False)
class FileLoggingConfig:
    type: Literal["file"]
    path: str


class CoreSection:
    debug: bool = False
    logging: list[StreamLoggingConfig] | None = None
