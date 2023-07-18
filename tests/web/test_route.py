from bolinette.core import meta
from bolinette.web import delete, get, patch, post, put, route
from bolinette.web.route import RouteBucket, RouteProps


def test_basic_route() -> None:
    @route("GET", "test")
    def test_route() -> None:
        pass

    route_bucket = meta.get(test_route, RouteBucket)
    assert route_bucket.name == "test_route"
    assert len(route_bucket.routes) == 1

    route_props = route_bucket[0]
    assert isinstance(route_props, RouteProps)
    assert route_props.method == "GET"
    assert route_props.real_path == "test"
    assert route_props.anon_path == "test"
    assert route_props.url_to_func_args == {}


def test_route_params() -> None:
    @route("GET", "thing/{id}")
    def test_route() -> None:
        pass

    route_bucket = meta.get(test_route, RouteBucket)
    assert route_bucket.name == "test_route"
    assert len(route_bucket.routes) == 1

    route_props = route_bucket[0]
    assert isinstance(route_props, RouteProps)
    assert route_props.method == "GET"
    assert route_props.real_path == "thing/{id}"
    assert route_props.anon_path == "thing/{_p0}"
    assert route_props.url_to_func_args == {"_p0": "id"}


def test_route_params_trailing_path() -> None:
    @route("GET", "thing/{id}/sub")
    def test_route() -> None:
        pass

    route_bucket = meta.get(test_route, RouteBucket)
    assert route_bucket.name == "test_route"
    assert len(route_bucket.routes) == 1

    route_props = route_bucket[0]
    assert isinstance(route_props, RouteProps)
    assert route_props.method == "GET"
    assert route_props.real_path == "thing/{id}/sub"
    assert route_props.anon_path == "thing/{_p0}/sub"
    assert route_props.url_to_func_args == {"_p0": "id"}


def test_route_multi_params() -> None:
    @route("GET", "thing/{id}/sub/{s_id}")
    def test_route() -> None:
        pass

    route_bucket = meta.get(test_route, RouteBucket)
    assert route_bucket.name == "test_route"
    assert len(route_bucket.routes) == 1

    route_props = route_bucket[0]
    assert isinstance(route_props, RouteProps)
    assert route_props.method == "GET"
    assert route_props.real_path == "thing/{id}/sub/{s_id}"
    assert route_props.anon_path == "thing/{_p0}/sub/{_p1}"
    assert route_props.url_to_func_args == {"_p0": "id", "_p1": "s_id"}


def test_multi_routes() -> None:
    @route("GET", "thing")
    @route("GET", "thing/{id}")
    def test_route() -> None:
        pass

    route_bucket = meta.get(test_route, RouteBucket)
    assert route_bucket.name == "test_route"
    assert len(route_bucket.routes) == 2

    route_props = route_bucket[0]
    assert isinstance(route_props, RouteProps)
    assert route_props.method == "GET"
    assert route_props.real_path == "thing/{id}"
    assert route_props.anon_path == "thing/{_p0}"
    assert route_props.url_to_func_args == {"_p0": "id"}

    route_props = route_bucket[1]
    assert isinstance(route_props, RouteProps)
    assert route_props.method == "GET"
    assert route_props.real_path == "thing"
    assert route_props.anon_path == "thing"
    assert route_props.url_to_func_args == {}


def test_special_routes() -> None:
    @get("thing/{id}")
    @post("thing")
    @put("thing/{id}")
    @patch("thing/{id}")
    @delete("thing/{id}")
    def test_route() -> None:
        pass

    route_bucket = meta.get(test_route, RouteBucket)
    assert len(route_bucket.routes) == 5
    assert route_bucket[0].method == "DELETE"
    assert route_bucket[0].url_to_func_args == {"_p0": "id"}
    assert route_bucket[1].method == "PATCH"
    assert route_bucket[1].url_to_func_args == {"_p0": "id"}
    assert route_bucket[2].method == "PUT"
    assert route_bucket[2].url_to_func_args == {"_p0": "id"}
    assert route_bucket[3].method == "POST"
    assert route_bucket[3].url_to_func_args == {}
    assert route_bucket[4].method == "GET"
    assert route_bucket[4].url_to_func_args == {"_p0": "id"}
