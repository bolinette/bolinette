from typing import Any

from bolinette.web.abstract import Request
from bolinette.web.exceptions import MethodNotAllowedDispatchError, NotFoundDispatchError
from bolinette.web.routing import Resource, ResourceNode, Route


class Router:
    def __init__(self) -> None:
        self.root_node: ResourceNode | None = None

    def add_route(self, route: Route[..., Any], /) -> None:
        new_node = ResourceNode.from_resource(Resource(route.path, [route]))
        if self.root_node is None:
            self.root_node = new_node
        else:
            self.root_node = ResourceNode.merge(self.root_node, new_node)

    def dispatch(self, request: Request) -> Route[..., Any]:
        def find_node(req_path: str, res_node: ResourceNode | None) -> ResourceNode | None:
            if not res_node or not len(req_path):
                return None
            length = res_node.match(req_path, request.path_params)
            if length <= 0:
                return None
            if length == len(req_path):
                return res_node
            req_path = req_path[length:]
            for subnode in res_node.subnodes:
                res = find_node(req_path, subnode)
                if res is not None:
                    return res
            return None

        node = find_node(request.path, self.root_node)
        if not node or not node.resource:
            raise NotFoundDispatchError(request.path)
        if request.method not in node.resource:
            raise MethodNotAllowedDispatchError(request.path)
        return node.resource[request.method]
