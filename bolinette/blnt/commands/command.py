from collections.abc import Callable

from bolinette.blnt.commands import Argument


class Command:
    def __init__(self, name: str, func: Callable, ):
        self.name = name
        self.func = func
        self.path: str | None = None
        self.summary: str | None = None
        self.args = []
        self.run_init: bool = False
        self.allow_anonymous: bool = False

    def init_params(self, path: str,summary: str,run_init: bool, allow_anonymous: bool):
        self.path = path
        self.summary = summary
        self.run_init = run_init
        self.allow_anonymous = allow_anonymous

    def init_args(self, *args: Argument):
        self.args = list(args) or []
