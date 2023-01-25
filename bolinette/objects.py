from typing import Any


class CoreSection:
    debug: bool = False


class GenericMeta:
    def __init__(self, args: tuple[Any, ...]) -> None:
        self.args = args
