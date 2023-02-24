from sqlalchemy.orm import DeclarativeBase

from bolinette import Cache, meta
from bolinette.ext.data.relational import get_base, DeclarativeMeta


def test_get_one_base() -> None:
    cache = Cache()

    base = get_base("test", cache=cache)

    assert issubclass(base, DeclarativeBase)
    assert DeclarativeMeta in cache
    assert meta.get(base, DeclarativeMeta).name == "test"
    assert base.__name__ == "TestDatabase"


def test_get_multiple_bases() -> None:
    cache = Cache()

    base1 = get_base("test1", cache=cache)
    base2 = get_base("test1", cache=cache)
    base3 = get_base("test3", cache=cache)

    assert base1 is base2
    assert base3 is not base1
    assert meta.get(base1, DeclarativeMeta).name == "test1"
    assert meta.get(base2, DeclarativeMeta).name == "test1"
    assert meta.get(base3, DeclarativeMeta).name == "test3"
