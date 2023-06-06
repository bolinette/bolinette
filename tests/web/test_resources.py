from aiohttp import web, ClientSession

from bolinette import Cache
from bolinette.testing import Mock
from bolinette.ext.web import Controller, controller, route, WebResources


async def start_server(app: web.Application) -> tuple[web.AppRunner, str]:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 0)
    await site.start()
    url, port = site._server.sockets[0].getsockname()  # type: ignore
    return runner, f"http://{url}:{port}"


async def stop_server(runner: web.AppRunner) -> None:
    await runner.cleanup()


async def test_call_basic_route() -> None:
    cache = Cache()

    class _TestCtrl(Controller):
        @route("GET", "route")
        async def get_by_id(self) -> web.Response:
            return web.Response(status=200, body="ok")

    controller("test", cache=cache)(_TestCtrl)

    mock = Mock(cache=cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    runner, url = await start_server(res.web_app)

    async with ClientSession(url) as session:
        async with session.get("/test/route") as resp:
            assert await resp.text() == "ok"

    await stop_server(runner)


async def test_call_route_with_args() -> None:
    cache = Cache()

    class _TestCtrl(Controller):
        @route("GET", "{id}")
        async def get_by_id(self, id: int) -> web.Response:
            return web.Response(status=200, body=f"{id}: {type(id)}")

    controller("test", cache=cache)(_TestCtrl)

    mock = Mock(cache=cache)
    mock.injection.add(WebResources, "singleton")

    res = mock.injection.require(WebResources)

    runner, url = await start_server(res.web_app)

    async with ClientSession(url) as session:
        async with session.get("/test/42") as resp:
            assert await resp.text() == f"42: {int}"

    await stop_server(runner)
