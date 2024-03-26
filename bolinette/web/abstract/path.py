import re
from collections.abc import Iterator
from typing import override


class WebPathNode:
    URL_PARAM_REGEX = re.compile(r"\{([a-zA-Z0-9_]+)(?::([^}]+))?\}")

    def __init__(self, origin: "str | WebPathNode", index: int = 0, /) -> None:
        match origin:
            case str():
                self.origin = origin
                self.pattern: re.Pattern[str] | None
                self.params: dict[int, str] = {}

                pattern_str: list[str] = []
                last_index = 0
                for p_index, match in enumerate(self.URL_PARAM_REGEX.finditer(origin), 1):
                    self.params[p_index] = match.group(1)
                    pattern_str.append(origin[last_index : match.start()])
                    if custom_pattern := match.group(2):
                        pattern_str.append(f"({custom_pattern})")
                    else:
                        pattern_str.append("(.*)")
                    last_index = match.end()
                if last_index > 0:
                    pattern_str.append(origin[last_index:])

                if pattern_str:
                    self.pattern = re.compile(f"^{"".join(pattern_str)}$")
                else:
                    self.pattern = None
            case WebPathNode():
                self.origin = origin.origin
                self.pattern = origin.pattern
                self.params = {**origin.params}
        self.index = index

    @override
    def __hash__(self) -> int:
        return hash(self.origin)

    @override
    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, WebPathNode):
            return NotImplemented
        if None not in (self.pattern, value.pattern):
            return self.pattern == value.pattern
        return self.origin == value.origin

    @override
    def __str__(self) -> str:
        return self.origin

    @override
    def __repr__(self) -> str:
        return f"<Node {self}>"


class WebPath:
    def __init__(self, path: "str | list[WebPathNode] | WebPath", /, *, absolute: bool | None = None) -> None:
        match path:
            case str():
                self.origin = path
                self.nodes = [WebPathNode(s, i) for i, s in enumerate(path.split("/")) if s]
            case list():
                self.origin = "/".join(n.origin for n in path)
                self.nodes = [WebPathNode(s, i) for i, s in enumerate(path) if s]
            case WebPath():
                self.origin = path.origin
                self.nodes = [WebPathNode(n, i) for i, n in enumerate(path.nodes)]
        if absolute and not self.origin.startswith("/"):
            self.origin = f"/{self.origin}"
        self.params = {p for n in self.nodes for p in n.params.values()}

    @property
    def is_absolute(self) -> bool:
        return self.origin.startswith("/")

    @override
    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, WebPath):
            return NotImplemented
        return self.nodes == value.nodes

    @override
    def __hash__(self) -> int:
        return hash(self.origin)

    def __iter__(self) -> Iterator[WebPathNode]:
        return iter(self.nodes)

    def __truediv__(self, value: "str | WebPathNode | WebPath", /) -> "WebPath":
        match value:
            case str():
                return WebPath([*self.nodes, WebPathNode(value)], absolute=self.is_absolute)
            case WebPathNode():
                return WebPath([*self.nodes, value], absolute=self.is_absolute)
            case WebPath():
                return WebPath([*self.nodes, *value.nodes], absolute=self.is_absolute)

    def __rtruediv__(self, value: "str | WebPathNode | WebPath", /) -> "WebPath":
        if self.is_absolute:
            raise ValueError("Cannot append an absolute web path to any path")
        match value:
            case str():
                return WebPath([*self.nodes, WebPathNode(value)])
            case WebPathNode():
                return WebPath([*self.nodes, value])
            case WebPath():
                return WebPath([*value.nodes, *self.nodes])

    @override
    def __str__(self) -> str:
        return self.origin

    @override
    def __repr__(self) -> str:
        return f"<WebPath {self}>"
