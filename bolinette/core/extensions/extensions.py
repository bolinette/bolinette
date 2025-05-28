from typing import Final, Protocol

from bolinette.core import Cache


class ExtensionModule[ExtT: "Extension"](Protocol):
    __blnt_ext__: Final[type[ExtT]]
    __name__: Final[str]


class Extension(Protocol):
    name: str
    dependencies: "list[ExtensionModule[Extension]]"

    def __init__(self, cache: Cache) -> None: ...
