from typing import Any, Awaitable, Callable

from aiohttp import web
from aiohttp.test_utils import TestClient

from bolinette import Cache
from bolinette.ext.web import Controller, WebResources, controller, route, with_middleware, get
from bolinette.testing import Mock

ClientFixture = Callable[[web.Application], Awaitable[TestClient]]


async def test_call_basic_route(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class _TestCtrl(Controller):
        @route("GET", "route")
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    controller("test", cache=cache)(_TestCtrl)

    mock = Mock(cache=cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test/route")

    assert resp.status == 200
    assert await resp.text() == "ok"


async def test_call_route_with_args(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    class _TestCtrl(Controller):
        @route("GET", "{id}")
        async def get_by_id(self, id: int) -> web.Response:
            return web.Response(status=200, body=f"{id}: {type(id)}")

    controller("test", cache=cache)(_TestCtrl)

    mock = Mock(cache=cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test/42")

    assert resp.status == 200
    assert await resp.text() == f"42: {int}"


async def test_call_route_with_middleware(aiohttp_client: ClientFixture) -> None:
    cache = Cache()

    order: list[str] = []

    class _CtrlMdlw:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("ctrl")
            return await next()

    class _RouteMdlw1:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("route1")
            return await next()

    class _RouteMdlw2:
        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            order.append("route2")
            return await next()

    @controller("test", cache=cache)
    @with_middleware(_CtrlMdlw)
    class _(Controller):
        @route("GET", "")
        @with_middleware(_RouteMdlw1)
        @with_middleware(_RouteMdlw2)
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    mock = Mock(cache=cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test")

    assert resp.status == 200
    assert await resp.text() == "ok"

    assert order == ["ctrl", "route1", "route2"]


async def test_intercept_request(aiohttp_client: ClientFixture) -> None:
    class _Auth:
        def __init__(self, request: web.Request) -> None:
            self.request = request

        def options(self) -> None:
            pass

        async def handle(self, next: Callable[[], Awaitable[web.Response]]) -> web.Response:
            if "x" not in self.request.headers:
                return web.Response(status=401)
            return await next()

    cache = Cache()

    @controller("test", cache=cache)
    @with_middleware(_Auth)
    class _(Controller):
        @get("")
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    mock = Mock(cache=cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    client = await aiohttp_client(res.web_app)
    resp = await client.get("/test")

    assert resp.status == 401
