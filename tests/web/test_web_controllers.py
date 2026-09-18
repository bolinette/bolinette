from typing import Any

import pytest
from escondite import Cache
from peritype import wrap_func, wrap_type

from bolinette.core import meta
from bolinette.web import AsgiApplication, Controller, controller, get
from bolinette.web._controller import ControllerMeta
from bolinette.web._resources import WebResources
from tests.web.conftest import AppFactory, AsgiClient


def _cached(cache: Cache) -> list[Any]:
    return list(cache.get(ControllerMeta.KEY, raises=False))


async def _client(make_app: AppFactory) -> AsgiClient:
    blnt = await make_app()
    return AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())


class TestControllerDecorator:
    def test_sets_metadata_and_caches_the_class(self, cache: Cache) -> None:
        @controller("items", cache=cache)
        class Ctrl(Controller):
            pass

        assert _cached(cache) == [Ctrl]
        ctrl_meta: ControllerMeta = meta.get(Ctrl, ControllerMeta.KEY)
        assert ctrl_meta.path == "items"

    def test_returns_the_class(self, cache: Cache) -> None:
        class Ctrl(Controller):
            pass

        assert controller("items", cache=cache)(Ctrl) is Ctrl


class TestRoutePaths:
    @pytest.mark.parametrize(
        ("ctrl_path", "route_path", "expected"),
        [
            ("items", "", "/items"),
            ("items", "all", "/items/all"),
            ("items/", "all", "/items/all"),
            ("", "all", "/all"),
            ("", "", "/"),
            ("items", "/absolute", "/absolute"),
        ],
    )
    async def test_paths_are_joined(self, make_app: AppFactory, ctrl_path: str, route_path: str, expected: str) -> None:
        class Ctrl:
            def handler(self) -> None:
                pass

        blnt = await make_app()
        resources = await blnt.injector.require(WebResources)

        resources.add_route(wrap_type(Ctrl), ctrl_path, wrap_func(Ctrl.handler), "GET", route_path)

        node = resources.router.root_node
        assert node is not None
        assert getattr(node, "path", None) == expected


class TestControllerResolution:
    async def test_routes_are_collected_from_the_cache(self, make_app: AppFactory, cache: Cache) -> None:
        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("all")
            async def all_items(self) -> str:
                return "all"

        client = await _client(make_app)

        assert (await client.request("GET", "/items/all")).text == "all"

    async def test_one_instance_per_request(self, make_app: AppFactory, cache: Cache) -> None:
        seen: list[int] = []

        @controller("items", cache=cache)
        class Ctrl(Controller):
            @get("")
            async def index(self) -> str:
                seen.append(id(self))
                return "ok"

        client = await _client(make_app)
        await client.request("GET", "/items")
        await client.request("GET", "/items")

        assert len(seen) == 2
        assert seen[0] != seen[1]

    async def test_inherited_routes_are_registered(self, make_app: AppFactory, cache: Cache) -> None:
        class BaseCtrl:
            @get("base")
            async def base_route(self) -> str:
                return "base"

        @controller("items", cache=cache)
        class Ctrl(BaseCtrl, Controller):
            @get("child")
            async def child_route(self) -> str:
                return "child"

        client = await _client(make_app)

        assert (await client.request("GET", "/items/base")).text == "base"
        assert (await client.request("GET", "/items/child")).text == "child"

    async def test_controller_dependencies_are_injected(self, make_app: AppFactory, cache: Cache) -> None:
        class Service:
            value = "injected"

        @controller("items", cache=cache)
        class Ctrl(Controller):
            def __init__(self, service: Service) -> None:
                self.service = service

            @get("")
            async def index(self) -> str:
                return self.service.value

        blnt = await make_app()
        blnt.injector.services.add_scoped(Service)
        client = AsgiClient((await blnt.injector.require(AsgiApplication)).get_app())

        assert (await client.request("GET", "/items")).text == "injected"
