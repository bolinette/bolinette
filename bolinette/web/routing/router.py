from typing import Any

from bolinette.web.abstract import Request, WebPath, WebPathNode
from bolinette.web.exceptions import MethodNotAllowedDispatchError, NotFoundDispatchError
from bolinette.web.routing import Resource, ResourceNode, Route


class Router:
    def __init__(self) -> None:
        self.root_node = ResourceNode(WebPathNode("/", 0), WebPath("/"))

    def add_route(self, route: Route[..., Any], /) -> None:
        node = self.root_node
        for path_node in route.path:
            for subnode in node.subnodes:
                if subnode.path_node == path_node:
                    node = subnode
                    break
            else:
                subnode = ResourceNode(path_node, node.fullpath / path_node)
                node.add_node(subnode)
                node = subnode
        if node.resource is None:
            node.resource = Resource(node.fullpath)
        node.resource.add(route)

    def dispatch(self, request: Request) -> Route[..., Any]:
        def find_node(req_path: list[str], res_node: ResourceNode) -> ResourceNode | None:
            if not len(req_path):
                return None
            for subnode in res_node.subnodes:
                if subnode.match(req_path[0], request.path_params):
                    if len(req_path) == 1:
                        return subnode
                    res = find_node(req_path[1:], subnode)
                    if res is not None:
                        return res
            return None

        request_path = [s for s in request.path.split("/") if s]
        node = find_node(request_path, self.root_node)
        if not node or not node.resource:
            raise NotFoundDispatchError(request.path)
        if request.method not in node.resource:
            raise MethodNotAllowedDispatchError(request.path)
        return node.resource[request.method]
