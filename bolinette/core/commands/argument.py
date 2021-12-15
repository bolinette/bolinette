from typing import Type, Literal


class Argument:
    def __init__(self, arg_type: Literal['arg', 'option', 'flag', 'count'],
                 name: str, *, flag: str = None, summary: str = None,
                 value_type: Type = None, default=None, choices: list = None):
        self.arg_type = arg_type
        self.name = name
        self.flag = flag
        self.summary = summary
        self.value_type = value_type
        self.default = default
        self.choices = choices
