from typing import List, Callable

from bolinette.blnt.commands import Argument


class Command:
    def __init__(self, name: str, func: Callable, summary: str, args: List[Argument]):
        self.name = name
        self.func = func
        self.summary = summary
        self.args = args or []
