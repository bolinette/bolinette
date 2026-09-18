from typing import Any

from muotti import Mapper


def to_json_value(mapper: Mapper, value: Any) -> Any:
    match value:
        case None | bool() | int() | float() | str():
            return value
        case bytes():
            return value.decode()
        case list() | tuple():
            return [to_json_value(mapper, item) for item in value]  # pyright: ignore[reportUnknownVariableType]
        case dict():
            return {str(key): to_json_value(mapper, item) for key, item in value.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
        case _:
            return mapper.map(dict[str, Any], value)
