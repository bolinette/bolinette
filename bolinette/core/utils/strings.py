import random
import re
import string
from collections.abc import Sequence
from typing import Any, Final


class StringUtils:
    __regex__: Final[dict[str, list[re.Pattern[str]]]] = {
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
    def random_string(length: int) -> str:
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def format_list(collection: Sequence[Any], *, sep: str = ", ", final_sep: str | None = None) -> str:
        formatted: list[str] = []
        cnt = len(collection)
        for i, e in enumerate(collection):
            formatted.append(str(e))
            if i != cnt - 1:
                if i == cnt - 2 and final_sep:
                    formatted.append(final_sep)
                else:
                    formatted.append(sep)
        return "".join(formatted)
