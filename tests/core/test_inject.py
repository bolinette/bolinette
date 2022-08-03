from typing import Callable

import pytest

from bolinette.core import Cache, Injection, InjectionStrategy, init_method
from bolinette.core.cache import RegisteredType
from bolinette.core.exceptions import InitError, InjectionError
from bolinette.core.inject import InjectionContext, _InjectionProxy


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
    inject = Injection(Cache(), InjectionContext())

    inject.add(InjectableClassA, InjectionStrategy.Singleton, None)
    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassA, InjectionStrategy.Singleton, None)

    assert f"Type {InjectableClassA} is already a registered type" in info.value.message


def test_instanciate_type_twice() -> None:
    inject = Injection(Cache(), InjectionContext())

    inject.add(InjectableClassB, InjectionStrategy.Singleton, None)
    inject._instanciate(inject._cache.get_type(InjectableClassB))
    with pytest.raises(InjectionError) as info:
        inject._instanciate(inject._cache.get_type(InjectableClassB))

    assert (
        f"Type {InjectableClassB} has already been instanciated" in info.value.message
    )


def test_class_injection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassA, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassD, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
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
    cache.add_type(InjectableClassA, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassD, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())

    inject.call(_test_func)


async def test_inject_call_async() -> None:
    async def _test_func(b: InjectableClassB):
        assert b.func() == "b"

    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())

    await inject.call(_test_func)


async def test_fail_injection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassC)

    assert (
        f"Type {InjectableClassC} is not a registered type in the injection system"
        in info.value.message
    )


async def test_fail_subinjection() -> None:
    cache = Cache()
    cache.add_type(InjectableClassD, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassD)

    assert (
        f"Type {InjectableClassC} is not a registered type in the injection system"
        in info.value.message
    )


def test_fail_call_injection() -> None:
    def _test_func(b: InjectableClassC):
        assert b.func() == "b"

    cache = Cache()

    inject = Injection(cache, InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.call(_test_func)

    assert (
        f"Type {InjectableClassC} is not a registered type in the injection system"
        in info.value.message
    )


def test_require_twice() -> None:
    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    b1 = inject.require(InjectableClassB)
    b2 = inject.require(InjectableClassB)

    assert b1 is b2


def test_add_instance_no_singleton() -> None:
    inject = Injection(Cache(), InjectionContext())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassB, InjectionStrategy.Transcient, instance=b)

    assert (
        f"Type {InjectableClassB} must be a singleton if an instance is provided"
        in info.value.message
    )


def test_add_instance_wrong_type() -> None:
    inject = Injection(Cache(), InjectionContext())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassA, InjectionStrategy.Singleton, instance=b)

    assert (
        f"Object provided must an instance of type {InjectableClassA}"
        in info.value.message
    )


def test_add_instance() -> None:
    inject = Injection(Cache(), InjectionContext())

    b = InjectableClassB()

    inject.add(InjectableClassB, InjectionStrategy.Singleton, instance=b)

    _b = inject.require(InjectableClassB)

    assert b is _b
    assert b.func() == b.func()


def test_no_literal_match() -> None:
    class _Value:
        pass

    class _TestClass:
        def __init__(self, value: "_Value") -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass}, Parameter 'value', "
        f"Literal '{_Value.__name__}' does not match any registered type"
        in info.value.message
    )


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
    cache.add_type(_TestClass, InjectionStrategy.Singleton)
    cache.add_type(_1_Value, InjectionStrategy.Singleton)
    cache.add_type(_2_Value, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass}, Parameter '_', "
        f"Literal '{_Value.__name__}' matches with 2 registered types, use a more explicit name"
        in info.value.message
    )


def test_no_annotation() -> None:
    class _TestClass:
        def __init__(self, _1, _2) -> None:
            pass

    cache = Cache()
    cache.add_type(_TestClass, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass}, Parameter '_1', Annotation is required"
        in info.value.message
    )


def test_use_init_method() -> None:
    class _TestClass:
        def __init__(self) -> None:
            self.value: str | None = None
            self.cls_name: str | None = None

        @init_method
        def init(self, b: InjectableClassB):
            self.value = b.func()
            self.cls_name = type(self).__name__

    class _ChildClass1(_TestClass):
        @init_method
        def sub_init(self, c: InjectableClassC):
            self.value = self.value + c.func() if self.value else c.func()

    class _ChildClass2(_TestClass):
        pass

    cache = Cache()
    cache.add_type(InjectableClassB, InjectionStrategy.Singleton)
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    inject.add(_ChildClass1, InjectionStrategy.Singleton)
    inject.add(_ChildClass2, InjectionStrategy.Singleton)

    t1 = inject.require(_ChildClass1)
    t2 = inject.require(_ChildClass2)

    assert t1.value == "bc"
    assert t2.value == "b"
    assert t1.cls_name == _ChildClass1.__name__
    assert t2.cls_name == _ChildClass2.__name__


def test_init_method_fail_decorate_type() -> None:
    class _TestClass:
        pass

    with pytest.raises(InitError) as info:
        init_method(_TestClass)

    assert (
        f"{_TestClass} must be a function to be decorated by {init_method.__name__}"
        in str(info.value)
    )


def test_arg_resolve_fail_wilcard() -> None:
    def _test_func(a, *args):
        pass

    inject = Injection(Cache(), InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, kwargs={"a": "a", "b": "b"})

    assert (
        f"Callable {_test_func}, Positional only parameters and positional wildcards are not allowed"
        in info.value.message
    )


def test_arg_resolve_fail_positional_only() -> None:
    def _test_func(a, /, b):
        pass

    inject = Injection(Cache(), InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, kwargs={"a": "a", "b": "b"})

    assert (
        f"Callable {_test_func}, Positional only parameters and positional wildcards are not allowed"
        in info.value.message
    )


def test_arg_resolve_fail_too_many_args() -> None:
    def _test_func(a, b) -> None:
        pass

    inject = Injection(Cache(), InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, args=["a", "b", "c"])

    assert f"Callable {_test_func}, Expected 2 arguments, 3 given" in info.value.message


def test_arg_resolve() -> None:
    def _test_func(a, b, c: InjectableClassC, d="d", **kwargs) -> None:
        assert a == "a"
        assert b == "b"
        assert c.func() == "c"
        assert d == "d"
        assert kwargs == {"e": "e", "f": "f"}

    cache = Cache()
    cache.add_type(InjectableClassC, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    inject.call(_test_func, args=["a"], kwargs={"b": "b", "e": "e", "f": "f"})


def test_two_injections() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    class _C3:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    cache = Cache()
    cache.add_type(_C1, InjectionStrategy.Singleton)
    cache.add_type(_C2, InjectionStrategy.Singleton)
    cache.add_type(_C3, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    c2 = inject.require(_C2)
    c3 = inject.require(_C3)

    assert c2.c1 is c3.c1


def test_transcient_injection() -> None:
    class _C1:
        pass

    class _C2:
        pass

    class _C3:
        def __init__(self, c1: _C1, c2: _C2) -> None:
            self.c1 = c1
            self.c2 = c2

    class _C4:
        def __init__(self, c1: _C1, c2: _C2) -> None:
            self.c1 = c1
            self.c2 = c2

    cache = Cache()
    cache.add_type(_C1, InjectionStrategy.Transcient)
    cache.add_type(_C2, InjectionStrategy.Singleton)
    cache.add_type(_C3, InjectionStrategy.Singleton)
    cache.add_type(_C4, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())
    c3 = inject.require(_C3)
    c4 = inject.require(_C4)

    assert c3.c2 is c4.c2
    assert c3.c1 is not c4.c1


def test_scoped_injection_fail_no_scope() -> None:
    class _C1:
        pass

    cache = Cache()
    cache.add_type(_C1, InjectionStrategy.Scoped)

    inject = Injection(cache, InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.require(_C1)

    assert (
        f"Type {_C1}, Cannot instanciate a scoped service outside of a scoped session"
        in info.value.message
    )


def test_scoped_injection() -> None:
    class _C1:
        pass

    class _C2:
        pass

    class _C3:
        pass

    class _C4:
        def __init__(self, c1: _C1, c2: _C2, c3: _C3) -> None:
            self.c1 = c1
            self.c2 = c2
            self.c3 = c3

    class _C5:
        def __init__(self, c1: _C1, c2: _C2, c3: _C3) -> None:
            self.c1 = c1
            self.c2 = c2
            self.c3 = c3

    cache = Cache()
    cache.add_type(_C1, InjectionStrategy.Transcient)
    cache.add_type(_C2, InjectionStrategy.Singleton)
    cache.add_type(_C3, InjectionStrategy.Scoped)
    cache.add_type(_C4, InjectionStrategy.Scoped)
    cache.add_type(_C5, InjectionStrategy.Scoped)

    inject = Injection(cache, InjectionContext())
    sub_inject1 = inject.get_scoped_session()
    c4_1 = sub_inject1.require(_C4)
    c5_1 = sub_inject1.require(_C5)
    sub_inject2 = inject.get_scoped_session()
    c4_2 = sub_inject2.require(_C4)

    assert c4_1 is not c4_2
    assert c4_1 is sub_inject1.require(_C4)
    assert c4_2 is sub_inject2.require(_C4)

    assert c4_1.c1 is not c4_2.c1
    assert c4_1.c2 is c4_2.c2
    assert c4_1.c3 is not c4_2.c3

    assert c4_1.c1 is not c5_1.c1
    assert c4_1.c2 is c5_1.c2
    assert c4_1.c3 is c5_1.c3


def test_require_transcient_service() -> None:
    class _C1:
        pass

    class _C2:
        pass

    cache = Cache()
    cache.add_type(_C1, InjectionStrategy.Transcient)
    cache.add_type(_C2, InjectionStrategy.Singleton)

    inject = Injection(cache, InjectionContext())

    assert inject.require(_C1) is not inject.require(_C1)
    assert inject.require(_C2) is inject.require(_C2)


def test_context_errors() -> None:
    class _C1:
        pass

    class _C2:
        pass

    ctx = InjectionContext()

    with pytest.raises(TypeError):
        (lambda x: x) in ctx

    with pytest.raises(TypeError):
        ctx[(lambda x: x)] = None

    c1_1 = _C1()
    c1_2 = _C1()

    ctx[_C1] = c1_1

    with pytest.raises(InjectionError):
        ctx[_C1] = c1_2

    with pytest.raises(TypeError):
        ctx[_C2] = c1_1

    with pytest.raises(InjectionError):
        _ = ctx[_C2]


def test_proxy_no_meta() -> None:
    r_type = RegisteredType(
        InjectableClassB, InjectionStrategy.Singleton, None, None, None
    )
    proxy = _InjectionProxy("test", r_type)

    with pytest.raises(InjectionError) as info:
        proxy.__get__(InjectableClassB(), None)

    assert (
        f"Type {r_type.cls} has not been intanciated through the injection system"
        in info.value.message
    )


def test_inject_nullable() -> None:
    class _SubTestClass:
        pass

    class _TestClass:
        def __init__(self, sub: _SubTestClass | None, i: int | None) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache(), InjectionContext())
    inject.add(_TestClass, InjectionStrategy.Singleton)

    t = inject.require(_TestClass)

    assert t.sub is None
    assert t.i is None


def test_inject_with_default() -> None:
    class _SubTestClass:
        pass

    s = _SubTestClass()

    class _TestClass:
        def __init__(self, sub: _SubTestClass = s, i: int = 3) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache(), InjectionContext())
    inject.add(_TestClass, InjectionStrategy.Singleton)

    t = inject.require(_TestClass)

    assert t.sub is s
    assert t.i is 3


def test_inject_no_union() -> None:
    class _TestClass:
        def __init__(self, v: int | bool) -> None:
            self.v = v

    inject = Injection(Cache(), InjectionContext())
    inject.add(_TestClass, InjectionStrategy.Singleton)

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass}, Parameter 'v', Type unions are not allowed"
        in info.value.message
    )


def test_not_compatible_type() -> None:
    class _TestClass:
        def __init__(self, v: Callable[[], None]) -> None:
            self.v = v

    inject = Injection(Cache(), InjectionContext())
    inject.add(_TestClass, InjectionStrategy.Singleton)

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        f"Callable {_TestClass}, Parameter 'v': Type hint is nor supported by the injection system"
        in info.value.message
    )
