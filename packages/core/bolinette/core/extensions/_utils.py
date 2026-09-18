from collections.abc import Sequence
from graphlib import CycleError, TopologicalSorter

from bolinette.core.exceptions import InitError
from bolinette.core.extensions._extensions import Extension


def sort_extensions[ExtT: Extension](
    extensions: Sequence[ExtT],
    *,
    first: Sequence[type[Extension]] = (),
) -> list[ExtT]:
    sorter: TopologicalSorter[type[Extension]] = TopologicalSorter()
    for ext in extensions:
        implied = () if type(ext) in first else first
        sorter.add(type(ext), *implied, *ext.dependencies)
    try:
        ordered_types = list(sorter.static_order())
    except CycleError as e:
        raise InitError("A circular dependency was detected in the loaded extensions") from e
    instance_map: dict[type[Extension], ExtT] = {type(ext): ext for ext in extensions}
    return [instance_map[t] for t in ordered_types if t in instance_map]


def resolve_extensions(
    extensions: Sequence[Extension],
    *,
    implicit: Sequence[type[Extension]] = (),
) -> list[Extension]:
    loaded: dict[type[Extension], Extension] = {}
    for ext in extensions:
        if type(ext) in loaded:
            raise InitError(f"Extension {type(ext).__qualname__} was provided twice")
        loaded[type(ext)] = ext

    def _load_pending(pending: list[type[Extension]]) -> set[type[Extension]]:
        seen: set[type[Extension]] = set()
        while pending:
            ext_type = pending.pop()
            if ext_type in seen:
                continue
            seen.add(ext_type)
            if ext_type in loaded:
                pending.extend(loaded[ext_type].dependencies)
                continue
            try:
                ext = ext_type()
            except TypeError as e:
                raise InitError(
                    f"Extension {ext_type.__qualname__} is required as a dependency but cannot be instantiated "
                    "without arguments; add it explicitly to the extensions list"
                ) from e
            loaded[ext_type] = ext
            pending.extend(ext.dependencies)
        return seen

    implicit_closure = _load_pending([*implicit])
    _load_pending([dep for ext in extensions for dep in ext.dependencies])

    return sort_extensions(list(loaded.values()), first=sorted(implicit_closure, key=lambda t: t.__qualname__))
