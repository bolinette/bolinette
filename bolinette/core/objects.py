from typing import Any


class CoreSection:
    debug: bool = False


class GenericMeta:
    def __init__(self, args: list[type[Any]]) -> None:
        self._args = args

    @property
    def args(self) -> list[type[Any]]:
        return list(self._args)
