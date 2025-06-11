import asyncio
import socket
from collections.abc import Awaitable, Callable

import aiohttp
import uvicorn

from bolinette import web
from bolinette.core import Bolinette, Cache
from bolinette.web.asgi import AsgiApplication
from bolinette.web.extension import WebExtension


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


async def run_test_server(
    cache: Cache,
    test_callback: Callable[[aiohttp.ClientSession], Awaitable[None]],
    web_ext_callback: Callable[[WebExtension], None] | None = None,
) -> None:
    server_ready = asyncio.Event()
    blnt_ready = asyncio.Event()
    startup_err: list[BaseException] = []
    tests_done = asyncio.Event()

    async def on_server_ready() -> None:
        server_ready.set()

    async def on_startup_complete() -> None:
        blnt_ready.set()

    async def on_startup_failed(err: BaseException) -> None:
        startup_err.append(err)
        blnt_ready.set()

    blnt = Bolinette(cache=cache)
    ext = blnt.use_extension(web)
    if web_ext_callback:
        web_ext_callback(ext)
    asgi_app = AsgiApplication(blnt.build())

    blnt.add_event_listener("server_startup_complete", on_startup_complete)
    blnt.add_event_listener("server_startup_failed", on_startup_failed)

    port = get_free_port()
    config = uvicorn.Config(asgi_app.get_app(), host="127.0.0.1", port=port, callback_notify=on_server_ready)
    server = uvicorn.Server(config)

    async def run_server() -> None:
        task = asyncio.create_task(server.serve())
        await tests_done.wait()
        task.cancel()

    async def run_tests() -> None:
        await blnt_ready.wait()
        if startup_err:
            raise startup_err[0]
        await server_ready.wait()
        async with aiohttp.ClientSession(f"http://127.0.0.1:{port}") as session:
            await test_callback(session)
        tests_done.set()

    await asyncio.gather(run_server(), run_tests())
