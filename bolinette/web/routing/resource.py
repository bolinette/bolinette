from typing import Any, override

from bolinette.core.types import Function, Type
from bolinette.web import Controller
from bolinette.web.abstract import WebPath, WebPathNode


class Route[**FuncP, FuncT]:
    def __init__(
        self,
        method: str,
        path: WebPath,
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
    def __init__(self, path: WebPath, /) -> None:
        self.path = path
        self.routes: dict[str, Route[..., Any]] = {}

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


class ResourceNode:
    def __init__(self, path_node: WebPathNode, fullpath: WebPath, /) -> None:
        self.path_node = path_node
        self.fullpath = fullpath
        self.resource: Resource | None = None
        self.subnodes: list[ResourceNode] = []

    def match(self, part: str, path_params: dict[str, str]) -> bool:
        if self.path_node.pattern is None:
            return self.path_node.origin == part
        match = self.path_node.pattern.match(part)
        if match is None:
            return False
        for index, param in self.path_node.params.items():
            path_params[param] = match.group(index)
        return True

    def set_resource(self, resource: Resource | None, /) -> None:
        self.resource = resource

    def add_node(self, node: "ResourceNode", /) -> None:
        self.subnodes.append(node)

    @override
    def __repr__(self) -> str:
        return (
            f"<ResourceNode {self.fullpath}: "
            f"{len(self.resource.routes) if self.resource else 0} routes, {len(self.subnodes)} subnodes>"
        )
