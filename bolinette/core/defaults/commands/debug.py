from typing import Any

from bolinette.core import Injection, __core_cache__, command


@command(
    "debug injection",
    "Prints every service registered in the injection system",
    cache=__core_cache__,
)
async def print_injection_debug_info(inject: Injection):
    def format_type(t: type[Any]) -> str:
        return f"{t.__module__}.{t.__qualname__}"

    for cls, bag in inject.registered_types.items():
        types = bag._types.values()
        last_index = len(types) - 1
        print(f"╔ {cls.__module__}.{cls.__qualname__}")
        if bag._match_all is not None:
            r_type = bag._match_all
            print(
                f"{'╠' if last_index > -1 else '╚'}═",
                f"Fallback: {format_type(r_type.cls)}",
            )
        for index, r_type in enumerate(types):
            print(
                f"{'╠' if index < last_index else '╚'}═",
                f"[{','.join(map(format_type, r_type.params))}]:",
                f"{format_type(r_type.cls)}",
            )
