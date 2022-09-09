import re


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
