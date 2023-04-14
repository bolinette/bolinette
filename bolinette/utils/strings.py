import random
import re
import string
from typing import Any


class StringUtils:
    __regex__ = {
        "snake": [
            re.compile(r"(.)([A-Z][a-z]+)"),
            re.compile(r"_+([A-Z])"),
            re.compile(r"([a-z0-9])([A-Z])"),
        ]
    }

    @staticmethod
    def to_snake_case(string: str):
        string = StringUtils.__regex__["snake"][0].sub(r"\1_\2", string)
        string = StringUtils.__regex__["snake"][1].sub(r"_\1", string)
        string = StringUtils.__regex__["snake"][2].sub(r"\1_\2", string)
        return string.lower()

    @staticmethod
    def capitalize(string: str):
        if not string:
            return string
        return f"{string[0].upper()}{string[1:]}"

    @staticmethod
    def random_string(length) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def format_type(__cls: type[Any], __type_vars: tuple[Any, ...]) -> str:
        if len(__type_vars) == 0:
            return str(__cls)
        return f"{__cls}[{','.join(str(t) for t in __type_vars)}]"
