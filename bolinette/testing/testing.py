from functools import wraps
import pytest

from bolinette import Bolinette, db
from bolinette.testing import TestClient


@pytest.fixture
def client():
    return TestClient(Bolinette(__name__, env={'ENV': 'test'}))


def bolitest(**options):
    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            db.drop_all()
            db.create_all()
            if 'before' in options and callable(options['before']):
                options['before']()
            yield func(*args, **kwargs)
            if 'after' in options and callable(options['after']):
                options['after']()
            db.drop_all()
        return inner
    return wrapper
