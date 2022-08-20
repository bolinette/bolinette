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
        c[_TestClass]
    with pytest.raises(KeyError):
        del c[_TestClass]
    with pytest.raises(KeyError):
        c.remove(_TestClass, t1)

    c.add(_TestClass, t1)
    assert _TestClass in c
    assert c[_TestClass] == [t1]

    c.add(_TestClass, t2)
    assert c[_TestClass] == [t1, t2]

    c.remove(_TestClass, t1)
    assert c[_TestClass] == [t2]

    del c[_TestClass]
    assert _TestClass not in c
