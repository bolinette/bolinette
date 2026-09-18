from typing import Any

import pytest
from peritype import wrap_func, wrap_type

from bolinette.core import meta
from bolinette.web import delete, get, patch, post, put, route
from bolinette.web._routing import Resource, ResourceNode, Route, RouteBucket, RouteProps, Router
from bolinette.web._routing._resource import PatternResourceNode, StaticResourceNode
from bolinette.web.exceptions import MethodNotAllowedDispatchError, NotFoundDispatchError


class Ctrl:
    def handler(self) -> None:
        pass


def _route(method: str, path: str) -> Route:
    return Route(method, path, wrap_type(Ctrl), wrap_func(Ctrl.handler))


class _Request:
    def __init__(self, method: str, path: str) -> None:
        self.method = method
        self.path = path
        self.headers: dict[str, str] = {}
        self.query_params: dict[str, list[str]] = {}
        self.path_params: dict[str, str] = {}

    async def raw(self) -> bytes:
        return b""

    async def text(self, *, encoding: str = "utf-8") -> str:
        return ""

    async def json(self, *, cls: Any = None) -> Any:
        return None

    def has_header(self, key: str, /) -> bool:
        return key in self.headers

    def get_header(self, key: str, /) -> str:
        return self.headers[key]


def _bucket(func: Any) -> RouteBucket:
    return meta.get(func, RouteBucket.KEY)


class TestRouteDecorators:
    def test_route_fills_a_bucket(self) -> None:
        @route("GET", "items")
        def handler() -> None:
            pass

        bucket = _bucket(handler)

        assert bucket.name == "handler"
        assert [(p.method, p.path) for p in bucket.routes] == [("GET", "items")]
        assert bucket[0].method == "GET"

    def test_stacked_decorators_share_one_bucket(self) -> None:
        @get("a")
        @post("b")
        @put("c")
        @patch("d")
        @delete("e")
        def handler() -> None:
            pass

        assert [(p.method, p.path) for p in _bucket(handler).routes] == [
            ("DELETE", "e"),
            ("PATCH", "d"),
            ("PUT", "c"),
            ("POST", "b"),
            ("GET", "a"),
        ]

    def test_bucket_add(self) -> None:
        bucket = RouteBucket("handler")
        props = RouteProps("GET", "a")

        bucket.add(props)

        assert bucket[0] is props


class TestResource:
    def test_add_and_lookup(self) -> None:
        resource = Resource("/items")
        route = _route("GET", "/items")

        resource.add(route)

        assert "GET" in resource
        assert resource["GET"] is route
        assert "POST" not in resource

    def test_add_rejects_another_path(self) -> None:
        with pytest.raises(ValueError, match="does not match resource path"):
            Resource("/items").add(_route("GET", "/other"))

    def test_merge_keeps_both_methods(self) -> None:
        merged = Resource("/items", [_route("GET", "/items")]) | Resource("/items", [_route("POST", "/items")])

        assert sorted(merged.routes) == ["GET", "POST"]

    def test_merge_rejects_different_paths(self) -> None:
        with pytest.raises(ValueError, match="same path"):
            _ = Resource("/items") | Resource("/other")

    def test_repr(self) -> None:
        assert repr(Resource("/items", [_route("GET", "/items")])) == "<Resource /items: 1 routes>"

    def test_route_repr_and_call(self) -> None:
        route = _route("GET", "/items")

        assert repr(route) == f"<Route GET /items -> {route.func}>"
        assert route(Ctrl()) is None


class TestResourceNodeConstruction:
    def test_static_only_path(self) -> None:
        node = ResourceNode.from_resource(Resource("/items"))

        assert isinstance(node, StaticResourceNode)
        assert node.path == "/items"
        assert node.subnodes == []

    def test_path_with_a_parameter(self) -> None:
        node = ResourceNode.from_resource(Resource("/items/{id}/tags"))

        assert isinstance(node, StaticResourceNode)
        assert node.path == "/items/"
        pattern = node.subnodes[0]
        assert isinstance(pattern, PatternResourceNode)
        assert pattern.param_name == "id"
        assert pattern.norm_pattern == "[^/]+"
        assert isinstance(pattern.subnodes[0], StaticResourceNode)

    def test_path_ending_on_a_parameter(self) -> None:
        node = ResourceNode.from_resource(Resource(r"/items/{id:\d+}"))

        pattern = node.subnodes[0]
        assert isinstance(pattern, PatternResourceNode)
        assert pattern.norm_pattern == r"\d+"
        assert pattern.resource is not None

    def test_path_starting_on_a_parameter_keeps_an_empty_static_root(self) -> None:
        node = ResourceNode.from_resource(Resource("{id}/tags"))

        assert isinstance(node, StaticResourceNode)
        assert node.path == ""
        assert isinstance(node.subnodes[0], PatternResourceNode)

    def test_empty_path_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="Empty path"):
            ResourceNode.from_resource(Resource(""))

    def test_set_resource(self) -> None:
        node = StaticResourceNode("/a", None, [])
        resource = Resource("/a")

        node.set_resource(resource)

        assert node.resource is resource

    def test_reprs(self) -> None:
        static = StaticResourceNode("/a", None, [])
        pattern = PatternResourceNode("id", None, None, None, [])

        assert repr(static) == "<ResourceNode /a 0 routes, 0 subnodes>"
        assert repr(pattern) == "<ResourceNode id:[^/]+ 0 routes, 0 subnodes>"


class TestResourceNodeMerge:
    def test_same_static_path(self) -> None:
        merged = ResourceNode.merge(
            StaticResourceNode("/a", Resource("/a", [_route("GET", "/a")]), []),
            StaticResourceNode("/a", Resource("/a", [_route("POST", "/a")]), []),
        )

        assert isinstance(merged, StaticResourceNode)
        assert merged.resource is not None
        assert sorted(merged.resource.routes) == ["GET", "POST"]

    def test_first_path_is_a_prefix(self) -> None:
        merged = ResourceNode.merge(
            StaticResourceNode("/a", Resource("/a"), []),
            StaticResourceNode("/ab", Resource("/ab"), []),
        )

        assert isinstance(merged, StaticResourceNode)
        assert merged.path == "/a"
        assert [n.path for n in merged.subnodes if isinstance(n, StaticResourceNode)] == ["b"]

    def test_second_path_is_a_prefix(self) -> None:
        merged = ResourceNode.merge(
            StaticResourceNode("/ab", Resource("/ab"), []),
            StaticResourceNode("/a", Resource("/a"), []),
        )

        assert isinstance(merged, StaticResourceNode)
        assert merged.path == "/a"

    def test_common_prefix_splits_both(self) -> None:
        merged = ResourceNode.merge(
            StaticResourceNode("/ab", Resource("/ab"), []),
            StaticResourceNode("/ac", Resource("/ac"), []),
        )

        assert isinstance(merged, StaticResourceNode)
        assert merged.path == "/a"
        assert merged.resource is None
        assert sorted(n.path for n in merged.subnodes if isinstance(n, StaticResourceNode)) == ["b", "c"]

    def test_two_equal_patterns(self) -> None:
        merged = ResourceNode.merge(
            PatternResourceNode("id", None, None, Resource("/x", [_route("GET", "/x")]), []),
            PatternResourceNode("id", None, None, None, []),
        )

        assert isinstance(merged, PatternResourceNode)
        assert merged.resource is not None

    def test_two_patterns_without_resources(self) -> None:
        merged = ResourceNode.merge(
            PatternResourceNode("id", None, None, None, []),
            PatternResourceNode("id", None, None, None, []),
        )

        assert merged.resource is None

    def test_pattern_resource_from_the_second_node(self) -> None:
        merged = ResourceNode.merge(
            PatternResourceNode("id", None, None, None, []),
            PatternResourceNode("id", None, None, Resource("/x"), []),
        )

        assert merged.resource is not None

    def test_different_patterns_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="Cannot merge different pattern"):
            ResourceNode.merge(
                PatternResourceNode("id", r"\d+", None, None, []),
                PatternResourceNode("name", r"\w+", None, None, []),
            )

    def test_mixing_static_and_pattern_is_rejected(self) -> None:
        with pytest.raises(TypeError, match="Cannot merge pattern path nodes"):
            ResourceNode.merge(
                StaticResourceNode("/a", None, []),
                PatternResourceNode("id", None, None, None, []),
            )

    def test_merge_subnodes_keeps_unrelated_nodes(self) -> None:
        merged = ResourceNode.merge_subnodes(
            [
                StaticResourceNode("/a", None, []),
                StaticResourceNode("b", None, []),
                PatternResourceNode("id", None, None, None, []),
                PatternResourceNode("id", None, None, None, []),
            ]
        )

        assert len(merged) == 3

    def test_merge_subnodes_picks_the_longest_common_prefix(self) -> None:
        merged = ResourceNode.merge_subnodes(
            [
                StaticResourceNode("abc", None, []),
                StaticResourceNode("xyz", None, []),
                StaticResourceNode("abd", None, []),
            ]
        )

        paths = sorted(n.path for n in merged if isinstance(n, StaticResourceNode))
        assert paths == ["ab", "xyz"]

    def test_merge_subnodes_folds_every_node_sharing_a_prefix(self) -> None:
        merged = ResourceNode.merge_subnodes(
            [
                StaticResourceNode("/abc", None, []),
                StaticResourceNode("/xyz", None, []),
            ]
        )

        assert [n.path for n in merged if isinstance(n, StaticResourceNode)] == ["/"]


class TestRouter:
    def test_dispatch_static_route(self) -> None:
        router = Router()
        route = _route("GET", "/items/all")
        router.add_route(route)

        assert router.dispatch(_Request("GET", "/items/all")) is route

    def test_dispatch_fills_path_params(self) -> None:
        router = Router()
        router.add_route(_route("GET", r"/items/{id:\d+}"))
        request = _Request("GET", "/items/42")

        router.dispatch(request)

        assert request.path_params == {"id": "42"}

    def test_dispatch_walks_several_branches(self) -> None:
        router = Router()
        router.add_route(_route("GET", "/items/all"))
        target = _route("GET", "/items/any")
        router.add_route(target)

        assert router.dispatch(_Request("GET", "/items/any")) is target

    def test_unknown_path_raises(self) -> None:
        router = Router()
        router.add_route(_route("GET", "/items"))

        with pytest.raises(NotFoundDispatchError):
            router.dispatch(_Request("GET", "/nope"))

    def test_empty_router_raises(self) -> None:
        with pytest.raises(NotFoundDispatchError):
            Router().dispatch(_Request("GET", "/items"))

    def test_partial_match_raises(self) -> None:
        router = Router()
        router.add_route(_route("GET", "/items/all"))

        with pytest.raises(NotFoundDispatchError):
            router.dispatch(_Request("GET", "/items"))

    def test_node_without_a_resource_raises(self) -> None:
        router = Router()
        router.add_route(_route("GET", "/ab"))
        router.add_route(_route("GET", "/ac"))

        with pytest.raises(NotFoundDispatchError):
            router.dispatch(_Request("GET", "/a"))

    def test_wrong_method_raises(self) -> None:
        router = Router()
        router.add_route(_route("GET", "/items"))

        with pytest.raises(MethodNotAllowedDispatchError):
            router.dispatch(_Request("POST", "/items"))


class TestNodeInternals:
    def test_the_base_match_is_abstract(self) -> None:
        with pytest.raises(NotImplementedError):
            ResourceNode(None, []).match("/a", {})

    def test_two_parameters_chain_static_nodes(self) -> None:
        node = ResourceNode.from_resource(Resource("/a/{x}/b/{y}/c"))

        assert isinstance(node, StaticResourceNode)
        first = node.subnodes[0]
        assert isinstance(first, PatternResourceNode)
        middle = first.subnodes[0]
        assert isinstance(middle, StaticResourceNode)
        assert middle.path == "/b/"

    def test_nodes_without_a_common_prefix_stay_apart(self) -> None:
        merged = ResourceNode.merge_subnodes([StaticResourceNode("a", None, []), StaticResourceNode("b", None, [])])

        assert sorted(n.path for n in merged if isinstance(n, StaticResourceNode)) == ["a", "b"]

    def test_a_static_node_ignores_pattern_nodes_when_merging(self) -> None:
        merged = ResourceNode.merge_subnodes(
            [PatternResourceNode("id", None, None, None, []), StaticResourceNode("a", None, [])]
        )

        assert len(merged) == 2

    def test_a_pattern_that_does_not_match_returns_zero(self) -> None:
        node = PatternResourceNode("id", r"\d+", None, None, [])

        assert node.match("abc", {}) == 0

    def test_a_path_that_no_subnode_matches_is_not_found(self) -> None:
        router = Router()
        router.add_route(_route("GET", "/a/b"))
        router.add_route(_route("GET", "/a/c"))

        with pytest.raises(NotFoundDispatchError):
            router.dispatch(_Request("GET", "/a/d"))
