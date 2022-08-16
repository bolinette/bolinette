from typing import Any


class CoreSection:
    debug: bool = False


class GenericMeta:
    def __init__(self, args: list[type[Any] | str]) -> None:
        self._args = args

    @property
    def args(self) -> list[type[Any] | str]:
        return [t for t in self._args]
