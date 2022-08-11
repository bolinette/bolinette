import pytest

from bolinette.core import Cache, InjectionStrategy, init_func, injectable
from bolinette.core.cache import _ParameterBag
from bolinette.core.exceptions import InitError
from bolinette.core.init import InitFunction


def test_empty_cache() -> None:
    cache = Cache()

    assert len(cache.types) == 0
    assert len(cache.init_funcs) == 0


def test_add_type() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, InjectionStrategy.Singleton)

    assert len(cache.types) == 1
    assert _TestClass in cache.types


def test_add_type_fail() -> None:
    class _TestClass:
        pass

    cache = Cache()

    with pytest.raises(TypeError):
        cache.types.add(_TestClass(), InjectionStrategy.Singleton)  # type: ignore


def test_get_of_type() -> None:
    class _ParentClass:
        pass

    class _ChildClass1(_ParentClass):
        pass

    class _ChildClass2(_ParentClass):
        pass

    cache = Cache()
    cache.types.add(_ChildClass1, InjectionStrategy.Singleton)
    cache.types.add(_ChildClass2, InjectionStrategy.Singleton)

    assert len(cache.types.of_type(_ParentClass)) == 2
    assert set(cache.types) == {_ChildClass1, _ChildClass2}


def test_add_init_func() -> None:
    async def _test_func() -> None:
        pass

    cache = Cache()
    cache.add_init_func(InitFunction(_test_func))

    assert len(cache.init_funcs) == 1


def test_injectable_decorator() -> None:
    cache = Cache()

    @injectable(cache=cache)
    class _TestClass:
        pass

    assert len(cache.types) == 1
    assert _TestClass in cache.types


def test_injectable_decorator_fail() -> None:
    def _test_func() -> None:
        pass

    cache = Cache()
    with pytest.raises(InitError) as info:
        injectable(cache=cache)(_test_func)  # type: ignore

    assert (
        f"'{_test_func}' must be a class to be decorated by @{injectable.__name__}"  # type: ignore
        in info.value.message
    )


def test_init_func_decorator() -> None:
    cache = Cache()

    @init_func(cache=cache)
    async def _() -> None:
        pass

    assert len(cache.init_funcs) == 1


def test_init_func_decorator_fail() -> None:
    class _TestClass:
        pass

    cache = Cache()
    with pytest.raises(InitError) as info:
        init_func(cache=cache)(_TestClass)  # type: ignore

    assert (
        f"'{_TestClass}' must be an async function to be an init function"  # type: ignore
        in info.value.message
    )


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
    cache.types.add(_TestClass, InjectionStrategy.Singleton, init_methods=[_init])

    assert cache.types.init_methods(_TestClass) == [_init]


def test_get_type_strategy() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, InjectionStrategy.Singleton)

    assert cache.types.strategy(_TestClass) is InjectionStrategy.Singleton


def test_get_type_args() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, InjectionStrategy.Singleton, args=[1, 2, 3])

    assert cache.types.args(_TestClass) == [1, 2, 3]


def test_get_type_kwargs() -> None:
    class _TestClass:
        pass

    cache = Cache()
    cache.types.add(_TestClass, InjectionStrategy.Singleton, kwargs={"a": 1, "b": 2})

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
