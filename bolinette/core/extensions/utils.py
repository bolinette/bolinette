from graphlib import CycleError, TopologicalSorter

from bolinette.core.exceptions import InitError
from bolinette.core.extensions import Extension


def sort_extensions(extensions: list[Extension]) -> list[Extension]:
    sorter: TopologicalSorter[type[Extension]] = TopologicalSorter()
    for ext in extensions:
        sorter.add(type(ext), *[m.__blnt_ext__ for m in ext.dependencies])
    try:
        ordered_types = list(sorter.static_order())
        instance_map = {type(ext): ext for ext in extensions}
        return [instance_map[t] for t in ordered_types]
    except CycleError as e:
        raise InitError("A circular dependency was detected in the loaded extensions") from e
