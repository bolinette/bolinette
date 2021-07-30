from collections.abc import Callable

from bolinette.blnt.commands import Argument


class Command:
    def __init__(self, name: str, func: Callable, path: str = None,
                 summary: str = None, args: list[Argument] = None, run_init: bool = False):
        self.name = name
        self.func = func
        self.path = path
        self.summary = summary
        self.args = args or []
        self.run_init = run_init
