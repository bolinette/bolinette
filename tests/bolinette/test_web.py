import asyncio
import socket

import aiohttp
import uvicorn

from bolinette import web
from bolinette.core import Bolinette, Cache
from bolinette.web import controller, get
from bolinette.web.asgi import AsgiApplication


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def test_call_basic_route() -> None:
    cache = Cache()

    server_ready = asyncio.Event()
    tests_done = asyncio.Event()

    async def on_server_started() -> None:
        server_ready.set()

    class TestController:
        @get("")
        async def test(self) -> str:
            return "Hello, world!"

    controller("/", cache=cache)(TestController)

    blnt = Bolinette(cache=cache)
    blnt.use_extension(web)
    asgi_app = AsgiApplication(blnt.build())

    port = _get_free_port()
    config = uvicorn.Config(asgi_app.get_app(), host="127.0.0.1", port=port, callback_notify=on_server_started)
    server = uvicorn.Server(config)

    async def run_server() -> None:
        task = asyncio.create_task(server.serve())
        await tests_done.wait()
        task.cancel()

    async def run_tests() -> None:
        await server_ready.wait()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:{port}/") as response:
                assert response.status == 200
                text = await response.text()
                assert text == "Hello, world!"
        tests_done.set()

    await asyncio.gather(run_server(), run_tests())
