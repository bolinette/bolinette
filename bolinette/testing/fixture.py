import random
import string

import pytest

from bolinette import Bolinette
from bolinette.testing import BolitestClient

bolinette_app = None


@pytest.fixture
def client(loop):
    global bolinette_app
    if bolinette_app is None:
        bolinette_app = Bolinette(profile='test', overrides={
            'secret_key': ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        })
        bolinette_app.init_bolinette()

    async def create_client():
        return BolitestClient(bolinette_app, loop)
    bolinette_app.init_extensions()
    return loop.run_until_complete(create_client())
