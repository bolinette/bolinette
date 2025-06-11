import aiohttp

from bolinette.core import Cache
from bolinette.core.testing import with_tmp_cwd_async
from bolinette.web import controller, get
from tests.bolinette.web_utils import run_test_server


@with_tmp_cwd_async
async def test_call_basic_route() -> None:
    cache = Cache()

    class TestController:
        @get("")
        async def test(self) -> str:
            return "Hello, world!"

    controller("/", cache=cache)(TestController)

    async def test_requests(session: aiohttp.ClientSession) -> None:
        async with session.get("/") as response:
            assert response.status == 200
            text = await response.text()
            assert text == "Hello, world!"

    await run_test_server(cache, test_requests)
