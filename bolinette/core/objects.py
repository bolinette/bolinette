from typing import Any


class GenericMeta:
    def __init__(self, args: tuple[Any, ...]) -> None:
        self.args = args
