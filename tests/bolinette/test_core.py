import importlib.util

import pytest

from bolinette.core import Bolinette, Cache, startup
from bolinette.core.testing import with_tmp_cwd_async

JINJA_INSTALLED = importlib.util.find_spec("jinja2") is not None


@with_tmp_cwd_async
async def test_start_bolinette() -> None:
    cache = Cache()
    blnt = Bolinette(cache=cache)

    order: list[str] = []

    def test_startup() -> None:
        order.append("startup")

    startup(cache=cache)(test_startup)

    await blnt.build().startup()

    assert order == ["startup"]


@pytest.mark.skipif(not JINJA_INSTALLED, reason="Jinja2 is not installed")
@with_tmp_cwd_async
async def test_init_jinja() -> None:
    from jinja2 import Environment, FunctionLoader

    cache = Cache()
    blnt = Bolinette(cache=cache)

    def loader_func(name: str) -> str:
        return f"templates/{name}.html.j2"

    loader = FunctionLoader(loader_func)
    blnt.core_extension.use_jinja_templating(loader=loader)

    await blnt.build().startup()

    assert not blnt.injection.is_registered(Environment)

    env = blnt.injection.require(Environment)

    assert env is not None
    assert env.loader is loader
    assert blnt.injection.is_registered(Environment)
