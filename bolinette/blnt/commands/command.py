from typing import List, Callable

from bolinette.blnt.commands import Argument


class Command:
    def __init__(self, name: str, func: Callable, path: str = None, summary: str = None, args: List[Argument] = None):
        self.name = name
        self.func = func
        self.path = path
        self.summary = summary
        self.args = args or []
