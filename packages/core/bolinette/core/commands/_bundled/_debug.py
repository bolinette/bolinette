from typing import Annotated, Any, override

from peritype import TWrap
from soupape import AsyncInjector, ServiceCollection
from soupape.extension import ServiceResolver

from bolinette.core.commands import CommandOption

type _TypeTree = dict[str, "_TypeTree | list[_RegisteredType]"]


class _RegisteredType:
    def __init__(self, interface: TWrap[Any], resolver: ServiceResolver[..., Any]) -> None:
        self.interface = interface
        self.resolver = resolver

    @override
    def __str__(self) -> str:
        registered = self.resolver.registered
        scope = self.resolver.scope.name.lower()
        if registered is None:
            return f"{self.interface}: {scope} ({self.resolver.name})"
        if registered == self.interface:
            return f"{self.interface}: {scope}"
        return f"{self.interface} -> {registered}: {scope}"


def build_type_tree(services: ServiceCollection, filter: str | None = None) -> _TypeTree:
    tree: _TypeTree = {}
    for interface in sorted(services.registered_types, key=str):
        cls = interface.origin
        module: str = getattr(cls, "__module__", None) or "<builtins>"
        qualname: str = getattr(cls, "__qualname__", None) or str(interface)
        full_name = f"{module}.{qualname}"
        if filter is not None and filter not in full_name:
            continue
        node = tree
        for part in module.split("."):
            child = node.setdefault(part, {})
            if isinstance(child, list):
                raise TypeError(f"Module path {module} conflicts with a registered type")
            node = child
        leaf = node.setdefault(qualname, [])
        if isinstance(leaf, dict):
            raise TypeError(f"Registered type {full_name} conflicts with a module path")
        leaf.append(_RegisteredType(interface, services.get_resolver(interface)))
    return tree


def format_type_tree(tree: _TypeTree, depth: int = 0) -> list[str]:
    lines: list[str] = []
    for key in sorted(tree):
        value = tree[key]
        indent = "  " * depth
        if isinstance(value, dict):
            lines.append(f"{indent}{key}")
            lines.extend(format_type_tree(value, depth + 1))
        else:
            lines.extend(f"{indent}{registered}" for registered in sorted(value, key=lambda r: str(r.interface)))
    return lines


async def debug_injection_command(
    inject: AsyncInjector,
    filter: Annotated[str | None, CommandOption("f", summary="Only show types whose name contains this")],
) -> None:
    print("=== All registered types in the injection system ===")
    for line in format_type_tree(build_type_tree(inject.services, filter)):
        print(line)
