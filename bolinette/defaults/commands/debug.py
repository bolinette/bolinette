from bolinette import __core_cache__, command
from bolinette.injection import Injection


@command(
    "debug injection",
    "Prints every service registered in the injection system",
    cache=__core_cache__,
)
async def print_injection_debug_info(inject: Injection):
    for cls, bag in inject.registered_types.items():
        types = bag._types.values()
        last_index = len(types) - 1
        print(f"╔ {cls.__module__}.{cls.__qualname__}")
        if bag._match_all is not None:
            r_type = bag._match_all
            print(f"{'╠' if last_index > -1 else '╚'}═Fallback: {r_type.t}")
        for index, r_type in enumerate(types):
            print(f"{'╠' if index < last_index else '╚'}═[{','.join(map(str, r_type.t.vars))}]:{r_type.t}")
