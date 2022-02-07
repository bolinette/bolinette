import random
import string
from asyncio import AbstractEventLoop

import pytest

from bolinette import Bolinette
from bolinette.web import ext as web_etx
from bolinette.testing import BolitestClient

bolinette_app = None


@pytest.fixture
def client(loop: AbstractEventLoop):
    global bolinette_app
    if bolinette_app is None:
        bolinette_app = Bolinette(
            profile="test",
            overrides={
                "secret_key": "".join(
                    random.choices(string.ascii_letters + string.digits, k=32)
                )
            },
        )
        bolinette_app.load(web_etx)
        loop.run_until_complete(bolinette_app.startup())

    async def create_client():
        return BolitestClient(bolinette_app.context, loop)

    loop.run_until_complete(bolinette_app.startup(first_run=False))
    return loop.run_until_complete(create_client())
