import random
import string

import pytest

from bolinette import Bolinette
from bolinette.testing import TestClient


@pytest.fixture
def client(loop):
    async def create_client():
        return TestClient(bolinette, loop)
    bolinette = Bolinette(profile='test', overrides={
        'secret_key': ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    })
    bolinette.init()
    return loop.run_until_complete(create_client())
