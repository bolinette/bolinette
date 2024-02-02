import pytest

from bolinette.core import Cache


def test_cache_use() -> None:
    class _TestClass:
        pass

    t1 = _TestClass()
    t2 = _TestClass()

    c = Cache()
    assert _TestClass not in c
    with pytest.raises(KeyError):
        c.get(_TestClass)
    with pytest.raises(KeyError):
        c.delete(_TestClass)
    with pytest.raises(KeyError):
        c.remove(_TestClass, t1)

    c.add(_TestClass, t1)
    assert _TestClass in c
    assert c.get(_TestClass) == [t1]

    c.add(_TestClass, t2)
    assert c.get(_TestClass) == [t1, t2]

    c.remove(_TestClass, t1)
    assert c.get(_TestClass) == [t2]

    c.delete(_TestClass)
    assert _TestClass not in c


def test_equality() -> None:
    c1 = Cache()
    c1.add(1, "a")
    c1.add(2, "a")

    c2 = Cache()
    c2.add(1, "a")

    c3 = Cache()
    c3.add(2, "b")

    c4 = Cache()
    c4.add(1, "b")

    assert c1 != c2
    assert c2 != c3
    assert c1 != c3
    assert c2 != c4
    assert c1 != object()


def test_merge_cache() -> None:
    c1 = Cache()
    c1.add(1, "a")

    c2 = Cache()
    c2.add(1, "b")
    c2.add(2, "a")

    c3 = c1 | c2

    assert c3.get(1) == ["a", "b"]
    assert c3.get(2) == ["a"]

    assert c3 == c1.__ror__(c2)
