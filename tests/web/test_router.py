import json
from typing import Any

import pytest

from bolinette.core.types import Function, Type
from bolinette.web.exceptions import MethodNotAllowedDispatchError, NotFoundDispatchError
from bolinette.web.routing import Route, Router
from bolinette.web.routing.resource import PatternResourceNode, StaticResourceNode


def test_add_route_same_path() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...
        def test_route_2(self) -> Any: ...

    router.add_route(Route("GET", "/", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("POST", "/", Type(Controller), Function(Controller.test_route_2)))

    assert router.root_node is not None
    assert router.root_node.resource is not None
    assert len(router.root_node.resource.routes) == 2
    assert {*router.root_node.resource.routes.keys()} == {"GET", "POST"}


def test_add_route_different_paths() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...
        def test_route_2(self) -> Any: ...

    router.add_route(Route("GET", "/get", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("POST", "/post", Type(Controller), Function(Controller.test_route_2)))

    assert router.root_node is not None
    assert router.root_node.resource is None
    assert len(router.root_node.subnodes) == 2
    get_node = next(n for n in router.root_node.subnodes if isinstance(n, StaticResourceNode) and n.path == "get")
    assert get_node.resource is not None and get_node.resource.routes["GET"].path == "/get"
    post_node = next(n for n in router.root_node.subnodes if isinstance(n, StaticResourceNode) and n.path == "post")
    assert post_node.resource is not None and post_node.resource.routes["POST"].path == "/post"


def test_add_route_longer_common_path() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...
        def test_route_2(self) -> Any: ...

    router.add_route(Route("GET", "/route", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/route-long-name", Type(Controller), Function(Controller.test_route_2)))

    assert router.root_node is not None
    assert router.root_node.resource is not None
    assert router.root_node.resource.path == "/route"
    assert len(router.root_node.subnodes) == 1
    node_res = router.root_node.subnodes[0]
    assert isinstance(node_res, StaticResourceNode) and node_res.path == "-long-name"
    assert node_res.resource is not None
    assert node_res.resource.path == "/route-long-name"


def test_add_route_shorter_common_path() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...
        def test_route_2(self) -> Any: ...

    router.add_route(Route("GET", "/route-long-name", Type(Controller), Function(Controller.test_route_2)))
    router.add_route(Route("GET", "/route", Type(Controller), Function(Controller.test_route_1)))

    assert router.root_node is not None
    assert router.root_node.resource is not None
    assert router.root_node.resource.path == "/route"
    assert len(router.root_node.subnodes) == 1
    node_res = router.root_node.subnodes[0]
    assert isinstance(node_res, StaticResourceNode) and node_res.path == "-long-name"
    assert node_res.resource is not None
    assert node_res.resource.path == "/route-long-name"


def test_add_multiple_routes() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/a/b/c", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/a/b/d/e", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/a/b/d/f", Type(Controller), Function(Controller.test_route_1)))

    assert router.root_node is not None
    assert router.root_node.resource is None
    assert isinstance(router.root_node, StaticResourceNode) and router.root_node.path == "/a/b/"
    assert len(router.root_node.subnodes) == 2
    c_node = next(n for n in router.root_node.subnodes if isinstance(n, StaticResourceNode) and n.path == "c")
    assert c_node.resource is not None and c_node.resource.path == "/a/b/c"
    d_node = next(n for n in router.root_node.subnodes if isinstance(n, StaticResourceNode) and n.path == "d/")
    assert d_node.resource is None
    assert len(d_node.subnodes) == 2
    e_node = next(n for n in d_node.subnodes if isinstance(n, StaticResourceNode) and n.path == "e")
    assert e_node.resource is not None and e_node.resource.path == "/a/b/d/e"
    f_node = next(n for n in d_node.subnodes if isinstance(n, StaticResourceNode) and n.path == "f")
    assert f_node.resource is not None and f_node.resource.path == "/a/b/d/f"


def test_add_routes_alternating_node_types() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/a/b/{c}/c", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/a/b/{c}/d", Type(Controller), Function(Controller.test_route_1)))

    assert router.root_node is not None
    assert router.root_node.resource is None
    assert isinstance(router.root_node, StaticResourceNode) and router.root_node.path == "/a/b/"
    assert len(router.root_node.subnodes) == 1
    node1 = router.root_node.subnodes[0]
    assert node1.resource is None
    assert isinstance(node1, PatternResourceNode)
    assert len(node1.subnodes) == 1
    node2 = node1.subnodes[0]
    assert node2.resource is None
    assert isinstance(node2, StaticResourceNode)
    assert len(node2.subnodes) == 2
    c_node = next(n for n in node2.subnodes if isinstance(n, StaticResourceNode) and n.path == "c")
    assert c_node.path == "c"
    assert c_node.resource is not None and c_node.resource.path == "/a/b/{c}/c"
    d_node = next(n for n in node2.subnodes if isinstance(n, StaticResourceNode) and n.path == "d")
    assert d_node.path == "d"
    assert d_node.resource is not None and d_node.resource.path == "/a/b/{c}/d"


def test_add_routes_conflicting_node_types() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/a/b/c", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/a/b/{c}", Type(Controller), Function(Controller.test_route_1)))

    assert router.root_node is not None
    assert router.root_node.resource is None
    assert isinstance(router.root_node, StaticResourceNode) and router.root_node.path == "/a/b/"
    assert len(router.root_node.subnodes) == 2
    static_node = next(n for n in router.root_node.subnodes if isinstance(n, StaticResourceNode))
    assert static_node.resource is not None and static_node.resource.path == "/a/b/c"
    pattern_node = next(n for n in router.root_node.subnodes if isinstance(n, PatternResourceNode))
    assert pattern_node.resource is not None and pattern_node.resource.path == "/a/b/{c}"


class MockRequest:
    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        query_params: dict[str, str],
        path_params: dict[str, str],
    ):
        self.method = method
        self.path = path
        self.headers = headers
        self.query_params = query_params
        self.path_params = path_params

    def has_header(self, key: str, /) -> bool: ...
    def get_header(self, key: str, /) -> str: ...

    async def raw(self) -> bytes: ...

    async def text(self, *, encoding: str = "utf-8") -> str: ...

    async def json(self, *, cls: type[json.JSONDecoder] | None = None) -> Any: ...


def test_dispatch_route() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/", Type(Controller), Function(Controller.test_route_1)))

    req = MockRequest("GET", "/", {}, {}, {})
    route = router.dispatch(req)

    assert route.method == "GET"
    assert route.path == "/"
    assert req.path_params == {}


def test_dispatch_route_amongst_many() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/a/b", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/a/c", Type(Controller), Function(Controller.test_route_1)))

    req = MockRequest("GET", "/a/c", {}, {}, {})
    route = router.dispatch(req)

    assert route.method == "GET"
    assert route.path == "/a/c"
    assert req.path_params == {}


def test_dispatch_route_in_resource() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("POST", "/", Type(Controller), Function(Controller.test_route_1)))

    req = MockRequest("POST", "/", {}, {}, {})
    route = router.dispatch(req)

    assert route.method == "POST"
    assert route.path == "/"
    assert req.path_params == {}


def test_dispatch_route_with_params() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/a/{b}/c", Type(Controller), Function(Controller.test_route_1)))

    req = MockRequest("GET", "/a/b/c", {}, {}, {})
    route = router.dispatch(req)

    assert route.method == "GET"
    assert route.path == "/a/{b}/c"
    assert req.path_params == {"b": "b"}


def test_dispatch_multiple_routes_with_params() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...
        def test_route_2(self) -> Any: ...

    router.add_route(Route("GET", r"/a/{b:\d+}/c", Type(Controller), Function(Controller.test_route_2)))
    router.add_route(Route("GET", "/a/{b}/c", Type(Controller), Function(Controller.test_route_1)))

    req = MockRequest("GET", "/a/1/c", {}, {}, {})
    route = router.dispatch(req)

    assert route.method == "GET"
    assert route.path == r"/a/{b:\d+}/c"
    assert req.path_params == {"b": "1"}
    assert route.func.func == Controller.test_route_2

    req = MockRequest("GET", "/a/b/c", {}, {}, {})
    route = router.dispatch(req)

    assert route.method == "GET"
    assert route.path == r"/a/{b}/c"
    assert req.path_params == {"b": "b"}
    assert route.func.func == Controller.test_route_1


def test_fail_dispatch_route_not_found() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/a", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("GET", "/b", Type(Controller), Function(Controller.test_route_1)))

    with pytest.raises(NotFoundDispatchError):
        router.dispatch(MockRequest("GET", "/c", {}, {}, {}))


def test_fail_dispatch_method_not_allowed() -> None:
    router = Router()

    class Controller:
        def test_route_1(self) -> Any: ...

    router.add_route(Route("GET", "/", Type(Controller), Function(Controller.test_route_1)))
    router.add_route(Route("POST", "/", Type(Controller), Function(Controller.test_route_1)))

    with pytest.raises(MethodNotAllowedDispatchError):
        router.dispatch(MockRequest("PUT", "/", {}, {}, {}))
