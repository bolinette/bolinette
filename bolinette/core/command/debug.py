from typing import Annotated, Any

from bolinette.core.command.command import Argument
from bolinette.core.injection import Injection
from bolinette.core.injection.registration import RegisteredTypeBag


async def debug_injection_command(inject: Injection, filter: Annotated[str | None, Argument("option")]) -> None:
    type_tree: dict[str, Any] = {}
    print("=== All registered types in the injection system ===")
    for type_name, bag in sorted(
        ((f"{c.__module__}.{c.__qualname__}", b) for c, b in inject.registered_types.items()),
        key=lambda t: t[0],
    ):
        if filter is not None and filter not in type_name:
            continue
        module_path = type_name.split(".")
        tree_node = type_tree
        index = 0
        while index < len(module_path) - 1:
            if index == len(module_path) - 2:
                part = f"{module_path[index]}.{module_path[index + 1]}"
            else:
                part = module_path[index]
            if part not in tree_node:
                if index == len(module_path) - 2:
                    tree_node[part] = bag
                else:
                    tree_node[part] = {}
            tree_node = tree_node[part]
            index += 1
    _print_type_tree(type_tree)


def _print_type_tree(tree: dict[str, Any], current_depth: int = 0) -> None:
    for key in tree:
        print(" " * 2 * current_depth, key, sep="")
        value: RegisteredTypeBag[Any] | dict[str, Any] = tree[key]
        if isinstance(value, dict):
            _print_type_tree(value, current_depth + 1)
        else:
            if match_all := value.match_all_type:
                print(" " * 2 * (current_depth + 1), match_all.t, ": ", match_all.strategy, " (match all)", sep="")
            for type in value.types:
                print(" " * 2 * (current_depth + 1), type.t, ": ", type.strategy, sep="")
