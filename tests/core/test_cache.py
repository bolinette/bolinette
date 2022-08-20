import pytest

from bolinette.core import Cache, init_func, injectable
from bolinette.core.cache import _ParameterBag
from bolinette.core.exceptions import InitError
from bolinette.core.init import InitFunction


def test_empty_cache() -> None:
    cache = Cache()

    assert len(cache.types) == 0
    assert len(cache.bag) == 0


def test_add_type() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, "singleton")

    assert len(cache.types) == 1
    assert _TestClass in cache.types


def test_add_type_fail() -> None:
    class _TestClass:
        pass

    cache = Cache()

    with pytest.raises(TypeError):
        cache.types.add(_TestClass(), "singleton")  # type: ignore


def test_get_of_type() -> None:
    class _ParentClass:
        pass

    class _ChildClass1(_ParentClass):
        pass

    class _ChildClass2(_ParentClass):
        pass

    cache = Cache()
    cache.types.add(_ChildClass1, "singleton")
    cache.types.add(_ChildClass2, "singleton")

    assert len(cache.types.of_type(_ParentClass)) == 2
    assert set(cache.types) == {_ChildClass1, _ChildClass2}


def test_injectable_decorator() -> None:
    cache = Cache()

    @injectable(cache=cache)
    class _TestClass:
        pass

    assert len(cache.types) == 1
    assert _TestClass in cache.types


def test_init_func_decorator() -> None:
    cache = Cache()

    @init_func(cache=cache)
    async def _() -> None:
        pass

    assert len(cache.bag[InitFunction]) == 1


def test_no_type_fail() -> None:
    class _TestClass:
        pass

    cache = Cache()

    with pytest.raises(KeyError):
        cache.types.strategy(_TestClass)

    with pytest.raises(KeyError):
        cache.types.init_methods(_TestClass)

    with pytest.raises(KeyError):
        cache.types.args(_TestClass)

    with pytest.raises(KeyError):
        cache.types.kwargs(_TestClass)


def test_get_type_init_method() -> None:
    class _TestClass:
        pass

    def _init(_: _TestClass):
        pass

    cache = Cache()
    cache.types.add(_TestClass, "singleton", init_methods=[_init])

    assert cache.types.init_methods(_TestClass) == [_init]


def test_get_type_strategy() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, "singleton")

    assert cache.types.strategy(_TestClass) == "singleton"


def test_get_type_args() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, "singleton", args=[1, 2, 3])

    assert cache.types.args(_TestClass) == [1, 2, 3]


def test_get_type_kwargs() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, "singleton", kwargs={"a": 1, "b": 2})

    assert cache.types.kwargs(_TestClass) == {"a": 1, "b": 2}


def test_param_bag_use() -> None:
    class _TestClass:
        pass

    t1 = _TestClass()
    t2 = _TestClass()

    p = _ParameterBag()
    assert _TestClass not in p
    with pytest.raises(KeyError):
        p[_TestClass]
    with pytest.raises(KeyError):
        del p[_TestClass]
    with pytest.raises(KeyError):
        p.remove(_TestClass, t1)

    p.push(_TestClass, t1)
    assert _TestClass in p
    assert p[_TestClass] == [t1]

    p.push(_TestClass, t2)
    assert p[_TestClass] == [t1, t2]

    p.remove(_TestClass, t1)
    assert p[_TestClass] == [t2]

    del p[_TestClass]
    assert _TestClass not in p
