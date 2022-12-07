from typing import Any


class CoreSection:
    debug: bool = False


class GenericMeta:
    def __init__(self, args: tuple[Any, ...]) -> None:
        self._args = args

    @property
    def args(self) -> tuple[Any, ...]:
        return tuple(self._args)
