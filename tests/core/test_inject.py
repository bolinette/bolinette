import pytest

from bolinette.core import Cache, Injection, inject
from bolinette.core.exceptions import InjectionError


class InjectableClassB:
    def __init__(self) -> None:
        pass

    def func(self) -> str:
        return "b"


class InjectableClassC:
    def __init__(self) -> None:
        pass

    def func(self) -> str:
        return "c"


class InjectableClassD:
    def __init__(self, c: InjectableClassC) -> None:
        self.c = c

    def func(self) -> str:
        return "d"


class InjectableClassA:
    def __init__(self, b: InjectableClassB, d_param: "InjectableClassD") -> None:
        self.b = b
        self.d_attr = d_param

    def func(self) -> str:
        return "a"


def test_add_type_twice() -> None:
    inject = Injection(Cache())

    inject.add(InjectableClassA)
    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassA)

    assert f"'{InjectableClassA}' is already a registered type" in info.value.message


def test_class_injection() -> None:
    cache = Cache()
    cache.add_type(
        InjectableClassA, InjectableClassB, InjectableClassC, InjectableClassD
    )

    inject = Injection(cache)
    a = inject.require(InjectableClassA)

    assert a.func() == "a"
    assert a.b.func() == "b"
    assert a.d_attr.func() == "d"
    assert a.d_attr.c.func() == "c"


def test_inject_call_sync() -> None:
    def _test_func(a: InjectableClassA):
        assert a.func() == "a"
        assert a.b.func() == "b"
        assert a.d_attr.func() == "d"
        assert a.d_attr.c.func() == "c"

    cache = Cache()
    cache.add_type(
        InjectableClassA, InjectableClassB, InjectableClassC, InjectableClassD
    )

    inject = Injection(cache)

    inject.call(_test_func)


async def test_inject_call_async() -> None:
    async def _test_func(b: InjectableClassB):
        assert b.func() == "b"

    cache = Cache()
    cache.add_type(InjectableClassB)

    inject = Injection(cache)

    await inject.call(_test_func)


async def test_fail_injection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassB)

    inject = Injection(cache)
    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassC)

    assert (
        f"'{InjectableClassC}' is not a registered type in the injection system"
        in info.value.message
    )


async def test_fail_subinjection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassD)

    inject = Injection(cache)
    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassD)

    assert (
        f"Errors raised while attemping to call '{InjectableClassD}'"
        in info.value.message
    )
    assert (
        f"'{InjectableClassC}' is not a registered type in the injection system"
        in info.value.message
    )


def test_fail_call_injection() -> None:
    def _test_func(b: InjectableClassC):
        assert b.func() == "b"

    cache = Cache()

    inject = Injection(cache)
    with pytest.raises(InjectionError) as info:
        inject.call(_test_func)

    assert f"Errors raised while attemping to call '{_test_func}'" in info.value.message
    assert (
        f"'{InjectableClassC}' is not a registered type in the injection system"
        in info.value.message
    )


def test_require_twice() -> None:
    cache = Cache()
    cache.add_type(InjectableClassB)

    inject = Injection(cache)
    b1 = inject.require(InjectableClassB)
    b2 = inject.require(InjectableClassB)

    assert b1 is b2


def test_no_literal_match() -> None:
    class _Value:
        pass

    class _TestClass:
        def __init__(self, value: "_Value") -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass)

    inject = Injection(cache)
    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert f"Literal '{_Value.__name__}' does not match any registered type" in info.value.message


def test_too_many_literal_matches() -> None:
    class _Value:
        pass
    class _1_Value:
        pass
    class _2_Value:
        pass

    class _TestClass:
        def __init__(self, _: "_Value") -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass, _1_Value, _2_Value)

    inject = Injection(cache)
    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert f"Literal '{_Value.__name__}' matches with 2 registered types, use a more explicit name" in info.value.message


def test_no_annotation() -> None:
    class _TestClass:
        def __init__(self, _1, _2) -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass)

    inject = Injection(cache)
    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert "'_1' param requires a type annotation" in info.value.message
    assert "'_2' param requires a type annotation" in info.value.message


def test_use_init_func() -> None:
    class _TestClass:
        def __init__(self) -> None:
            self.value: str | None = None
            self.cls_name: str | None = None

    def _test_func(t: _TestClass, b: InjectableClassB):
        t.value = b.func()
        t.cls_name = type(t).__name__

    class _ChildClass1(_TestClass):
        pass

    class _ChildClass2(_TestClass):
        pass

    cache = Cache()
    cache.add_type(InjectableClassB)

    inject = Injection(cache)
    inject.add(_ChildClass1, func=_test_func)
    inject.add(_ChildClass2, func=_test_func)

    t1 = inject.require(_ChildClass1)
    t2 = inject.require(_ChildClass2)

    assert t1.value == "b"
    assert t2.value == "b"
    assert t1.cls_name == _ChildClass1.__name__
    assert t2.cls_name == _ChildClass2.__name__
