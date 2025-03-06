from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jinja2 import BaseLoader


class JinjaConfig:
    def __init__(self, loader: "BaseLoader | None") -> None:
        self.loader = loader
