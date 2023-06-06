from typing import Awaitable, Callable

from aiohttp import web
from aiohttp.test_utils import TestClient

from bolinette import Cache
from bolinette.ext.web import Controller, WebResources, controller, route
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
