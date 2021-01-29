from enum import Enum, unique, auto
from typing import Type


@unique
class ArgType(Enum):
    Argument = auto()
    Option = auto()
    Flag = auto()
    Count = auto()


class Argument:
    def __init__(self, arg_type: ArgType, name: str, *, flag: str = None, summary: str = None,
                 value_type: Type = None, default=None, choices: list = None):
        self.arg_type = arg_type
        self.name = name
        self.flag = flag
        self.summary = summary
        self.value_type = value_type
        self.default = default
        self.choices = choices
