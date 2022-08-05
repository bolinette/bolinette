from typing import Any


class CoreSection:
    debug: bool = False


class GenericMeta:
    def __init__(self, templates: list[type[Any] | str]) -> None:
        self._templates = templates

    @property
    def templates(self) -> list[type[Any] | str]:
        return [t for t in self._templates]
