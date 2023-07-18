from bolinette.core import Cache
from bolinette.core.exceptions import InitError


class Extension:
    def __init__(self, cache: Cache, dependencies: "list[Extension] | None" = None) -> None:
        self.cache = cache
        self.dependencies = dependencies or []

    @staticmethod
    def sort_extensions(extensions: "list[Extension]") -> "list[Extension]":
        dependencies: dict[Extension, set[Extension]] = {}
        for extension in extensions:
            dependencies[extension] = set(extension.dependencies)
        sorted_extensions: list[Extension] = []
        while len(sorted_extensions) != len(extensions):
            no_dependencies: list[Extension] = []
            for extension, deps in dependencies.items():
                if not deps:
                    no_dependencies.append(extension)
            if len(no_dependencies) == 0:
                raise InitError("A circular dependency was detected in the loaded extensions")
            for extension in no_dependencies:
                sorted_extensions.append(extension)
                del dependencies[extension]
                for other_extension in dependencies:
                    if extension in dependencies[other_extension]:
                        dependencies[other_extension].remove(extension)
        return sorted_extensions

    @staticmethod
    def merge_caches(extensions: "list[Extension]") -> Cache:
        cache = Cache()
        for extension in extensions:
            cache |= extension.cache
        return cache


core_ext = Extension(Cache())
