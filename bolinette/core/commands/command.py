from typing import Any
from collections.abc import Callable
from bolinette.core import BolinetteExtension
from bolinette.core.commands import Argument


class Command:
    def __init__(self, name: str, func: Callable):
        self.name = name
        self.func = func
        self.path: str | None = None
        self.summary: str | None = None
        self.args: list[Any] = []
        self.exts: list[BolinetteExtension] = []
        self.allow_anonymous: bool = False

    def init_params(
        self,
        path: str,
        summary: str,
        exts: list[BolinetteExtension],
        allow_anonymous: bool,
    ):
        self.path = path
        self.summary = summary
        self.exts = exts
        self.allow_anonymous = allow_anonymous

    def init_args(self, *args: Argument):
        self.args = list(args) or []
