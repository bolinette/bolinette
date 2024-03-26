import os
import re
from typing import Any, override

from bolinette.core.types import Function, Type
from bolinette.web import Controller


class Route[**FuncP, FuncT]:
    def __init__(
        self,
        method: str,
        path: str,
        controller: Type[Controller],
        func: Function[FuncP, FuncT],
    ) -> None:
        self.method = method
        self.controller = controller
        self.func = func
        self.path = path

    def __call__(self, *args: FuncP.args, **kwargs: FuncP.kwargs) -> FuncT:
        return self.func(*args, **kwargs)

    @override
    def __repr__(self) -> str:
        return f"<Route {self.method} {self.path} -> {self.func}>"


class Resource:
    def __init__(self, path: str, routes: list[Route[..., Any]] | None = None, /) -> None:
        self.path = path
        self.routes = {r.method: r for r in routes or []}

    def add(self, route: Route[..., Any], /) -> None:
        if route.path != self.path:
            raise ValueError()  # TODO
        self.routes[route.method] = route

    def __getitem__(self, method: str, /) -> Route[..., Any]:
        return self.routes[method]

    def __contains__(self, method: str, /) -> bool:
        return method in self.routes

    @override
    def __repr__(self) -> str:
        return f"<Resource {self.path}: {len(self.routes)} routes>"

    def __or__(self, res: "Resource") -> "Resource":
        if self.path != res.path:
            raise ValueError("Resources must have the same path to be merged")
        new_res = Resource(self.path)
        new_res.routes = self.routes | res.routes
        return new_res


class ResourceNode:
    _PATH_PARAM_REGEX = re.compile(r"\{([^}:]+)(?:\:([^}]+))?\}")

    def __init__(
        self,
        resource: Resource | None,
        subnodes: "list[ResourceNode]",
    ) -> None:
        self.resource = resource
        self.subnodes = subnodes

    def match(self, path: str, path_params: dict[str, str]) -> int:
        raise NotImplementedError()

    def set_resource(self, resource: Resource | None, /) -> None:
        self.resource = resource

    def add_subnode(self, node: "ResourceNode", /) -> None:
        self.subnodes.append(node)

    @staticmethod
    def from_resource(resource: Resource) -> "ResourceNode":
        origin = resource.path
        first_node: ResourceNode | None = None
        last_node: ResourceNode | None = None
        last_index = 0
        for match in ResourceNode._PATH_PARAM_REGEX.finditer(origin):
            pattern_node = PatternResourceNode(match.group(1), match.group(2), None, None, [])
            static_node = StaticResourceNode(origin[last_index : match.start()], None, [pattern_node])
            if last_node is not None:
                last_node.add_subnode(static_node)
            if first_node is None:
                first_node = static_node
            last_node = pattern_node
            last_index = match.end()
        if last_index < len(origin):
            static_node = StaticResourceNode(origin[last_index:], resource, [])
            if last_node is not None:
                last_node.add_subnode(static_node)
            if first_node is None:
                first_node = static_node
        elif last_node is not None:
            last_node.resource = resource
        if first_node is None:
            raise ValueError("Empty path")
        return first_node

    @staticmethod
    def merge(n1: "ResourceNode", n2: "ResourceNode") -> "ResourceNode":
        def merge_resources(r1: Resource | None, r2: Resource | None) -> Resource | None:
            if r1 is None and r2 is None:
                return None
            if r1 is not None and r2 is None:
                return r1
            if r1 is None and r2 is not None:
                return r2
            if r1 is not None and r2 is not None:
                return r1 | r2

        if isinstance(n1, PatternResourceNode) and isinstance(n2, PatternResourceNode):
            if n1.param_name != n2.param_name and n1.norm_pattern != n2.norm_pattern:
                raise ValueError("Cannot merge different pattern")
            return PatternResourceNode(
                n1.param_name,
                n1.pattern,
                n1.norm_pattern,
                merge_resources(n1.resource, n2.resource),
                ResourceNode.merge_subnodes([*n1.subnodes, *n2.subnodes]),
            )

        if not isinstance(n1, StaticResourceNode) or not isinstance(n2, StaticResourceNode):
            raise TypeError("Cannot merge pattern path nodes")
        if n1.path == n2.path:
            return StaticResourceNode(
                n1.path,
                merge_resources(n1.resource, n2.resource),
                ResourceNode.merge_subnodes([*n1.subnodes, *n2.subnodes]),
            )
        common_path = os.path.commonprefix([n1.path, n2.path])
        if common_path == n1.path:
            return StaticResourceNode(
                common_path,
                n1.resource,
                ResourceNode.merge_subnodes(
                    [
                        *n1.subnodes,
                        StaticResourceNode(n2.path[len(common_path) :], n2.resource, n2.subnodes),
                    ]
                ),
            )
        elif common_path == n2.path:
            return StaticResourceNode(
                common_path,
                n2.resource,
                ResourceNode.merge_subnodes(
                    [
                        StaticResourceNode(n1.path[len(common_path) :], n1.resource, n1.subnodes),
                        *n2.subnodes,
                    ]
                ),
            )
        else:
            return StaticResourceNode(
                common_path,
                None,
                [
                    StaticResourceNode(n1.path[len(common_path) :], n1.resource, n1.subnodes),
                    StaticResourceNode(n2.path[len(common_path) :], n2.resource, n2.subnodes),
                ],
            )

    @staticmethod
    def merge_subnodes(nodes: "list[ResourceNode]") -> "list[ResourceNode]":
        merged_nodes: list[ResourceNode] = []
        for node in nodes:
            closest_match: tuple[str, int, ResourceNode] | None = None
            if isinstance(node, StaticResourceNode):
                for node_index, merged_node in enumerate(merged_nodes):
                    if not isinstance(merged_node, StaticResourceNode):
                        continue
                    common_path = os.path.commonprefix([node.path, merged_node.path])
                    if not len(common_path):
                        continue
                    if closest_match is None or len(common_path) > len(closest_match[0]):
                        closest_match = (common_path, node_index, merged_node)
            elif isinstance(node, PatternResourceNode):
                for node_index, merged_node in enumerate(merged_nodes):
                    if not isinstance(merged_node, PatternResourceNode):
                        continue
                    if node.param_name == merged_node.param_name and node.norm_pattern == merged_node.norm_pattern:
                        closest_match = ("", node_index, merged_node)
            if closest_match is None:
                merged_nodes.append(node)
            else:
                merged_nodes[closest_match[1]] = ResourceNode.merge(node, closest_match[2])
        return merged_nodes


class StaticResourceNode(ResourceNode):
    def __init__(
        self,
        path: str,
        resource: Resource | None,
        subnodes: list[ResourceNode],
    ) -> None:
        super().__init__(resource, subnodes)
        self.path = path

    @override
    def match(self, path: str, path_params: dict[str, str]) -> int:
        if path.startswith(self.path):
            return len(self.path)
        return 0

    @override
    def __repr__(self) -> str:
        return (
            f"<ResourceNode {self.path} "
            f"{len(self.resource.routes) if self.resource else 0} routes, {len(self.subnodes)} subnodes>"
        )


class PatternResourceNode(ResourceNode):
    def __init__(
        self,
        param_name: str,
        pattern: str | None,
        norm_pattern: str | None,
        resource: Resource | None,
        subnodes: list[ResourceNode],
    ) -> None:
        super().__init__(resource, subnodes)
        self.param_name = param_name
        self.pattern = pattern
        if norm_pattern is not None:
            self.norm_pattern = norm_pattern
        else:
            self.norm_pattern = pattern or "[^/]+"
        self.regex = re.compile(f"({self.norm_pattern})")

    @override
    def match(self, path: str, path_params: dict[str, str]) -> int:
        if match := self.regex.match(path):
            group = match.group(1)
            path_params[self.param_name] = group
            return len(group)
        return 0

    @override
    def __repr__(self) -> str:
        return (
            f"<ResourceNode {self.param_name}:{self.norm_pattern} "
            f"{len(self.resource.routes) if self.resource else 0} routes, {len(self.subnodes)} subnodes>"
        )
