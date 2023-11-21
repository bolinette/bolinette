# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
from types import TracebackType
from typing import Any, Self, TypeVar

import pytest

from bolinette.core import Cache, GenericMeta, meta
from bolinette.core.exceptions import InjectionError, TypingError
from bolinette.core.injection import Injection, init_method, injectable, require
from bolinette.core.injection.resolver import ArgResolverOptions, injection_arg_resolver


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


class _SubTestClass:
    pass


def test_class_injection() -> None:
    inject = Injection(Cache())
    inject.add(InjectableClassA, "singleton")
    inject.add(InjectableClassB, "singleton")
    inject.add(InjectableClassC, "singleton")
    inject.add(InjectableClassD, "singleton")

    a = inject.require(InjectableClassA)

    assert a.func() == "a"
    assert a.b.func() == "b"
    assert a.d_attr.func() == "d"
    assert a.d_attr.c.func() == "c"

    assert {
        InjectableClassA,
        InjectableClassB,
        InjectableClassC,
        InjectableClassD,
        Injection,
        Cache,
    } == set(inject.registered_types)


def test_class_injection_from_cache() -> None:
    cache = Cache()

    injectable(cache=cache)(InjectableClassA)
    injectable(cache=cache)(InjectableClassB)
    injectable(cache=cache)(InjectableClassC)
    injectable(cache=cache, match_all=True)(InjectableClassD)

    inject = Injection(cache)

    a = inject.require(InjectableClassA)

    assert a.func() == "a"
    assert a.b.func() == "b"
    assert a.d_attr.func() == "d"
    assert a.d_attr.c.func() == "c"


def test_inject_call_sync() -> None:
    def _test_func(a: InjectableClassA) -> None:
        assert a.func() == "a"
        assert a.b.func() == "b"
        assert a.d_attr.func() == "d"
        assert a.d_attr.c.func() == "c"

    inject = Injection(Cache())
    inject.add(InjectableClassA, "singleton")
    inject.add(InjectableClassB, "singleton")
    inject.add(InjectableClassC, "singleton")
    inject.add(InjectableClassD, "singleton")

    inject.call(_test_func)


async def test_inject_call_async() -> None:
    async def _test_func(b: InjectableClassB) -> None:
        assert b.func() == "b"

    inject = Injection(Cache())
    inject.add(InjectableClassB, "singleton")

    await inject.call(_test_func)


async def test_fail_injection() -> None:
    inject = Injection(Cache())
    inject.add(InjectableClassB, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassC)

    assert "Type InjectableClassC is not a registered type in the injection system" == info.value.message


async def test_fail_injection_generic() -> None:
    class _Param:
        pass

    class _Service[T]:
        pass

    inject = Injection(Cache())

    with pytest.raises(InjectionError) as info:
        inject.require(_Service[_Param])

    assert (
        "Type test_fail_injection_generic.<locals>._Service[test_fail_injection_generic.<locals>._Param] "
        "is not a registered type in the injection system" == info.value.message
    )


async def test_fail_subinjection() -> None:
    inject = Injection(Cache())
    inject.add(InjectableClassD, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassD)

    assert (
        "Callable InjectableClassD, Parameter 'c', "
        "Type InjectableClassC is not a registered type in the injection system" == info.value.message
    )


async def test_fail_subinjection_generic() -> None:
    class _Param:
        pass

    class _SubService[T]:
        pass

    class _Service:
        def __init__(self, sub: _SubService[_Param]) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_Service, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_Service)

    assert (
        "Callable test_fail_subinjection_generic.<locals>._Service, Parameter 'sub', "
        "Type test_fail_subinjection_generic.<locals>._SubService[test_fail_subinjection_generic.<locals>._Param] "
        "is not a registered type in the injection system" == info.value.message
    )


def test_fail_call_injection() -> None:
    def _test_func(b: InjectableClassC) -> None:
        assert b.func() == "b"

    inject = Injection(Cache())
    with pytest.raises(InjectionError) as info:
        inject.call(_test_func)

    assert (
        "Callable test_fail_call_injection.<locals>._test_func, Parameter 'b', "
        "Type InjectableClassC is not a registered type in the injection system" == info.value.message
    )


def test_require_twice() -> None:
    inject = Injection(Cache())
    inject.add(InjectableClassB, "singleton")

    b1 = inject.require(InjectableClassB)
    b2 = inject.require(InjectableClassB)

    assert b1 is b2


def test_add_instance_no_singleton() -> None:
    inject = Injection(Cache())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassB, "transient", instance=b)

    assert (
        f"Injection strategy for {InjectableClassB} must be singleton if an instance is provided" == info.value.message
    )


def test_add_instance_wrong_type() -> None:
    inject = Injection(Cache())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassA, "singleton", instance=b)

    assert f"Object provided must an instance of type {InjectableClassA}" == info.value.message


def test_add_instance() -> None:
    inject = Injection(Cache())

    b = InjectableClassB()

    inject.add(InjectableClassB, "singleton", instance=b)

    _b = inject.require(InjectableClassB)

    assert b is _b
    assert b.func() == b.func()


def test_forward_ref_local_class_not_resolved() -> None:
    class _Value:
        pass

    class _TestClass:
        def __init__(self, value: "_Value") -> None:
            pass

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        "Callable test_forward_ref_local_class_not_resolved.<locals>._TestClass, "
        "Type hint '_Value' could not be resolved" == info.value.message
    )


def test_no_annotation() -> None:
    class _TestClass:
        def __init__(self, _1, _2) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        "Callable test_no_annotation.<locals>._TestClass, Parameter '_1', Annotation is required" == info.value.message
    )


def test_use_init_method() -> None:
    class _TestClass:
        def __init__(self) -> None:
            self.value: str | None = None
            self.cls_name: str | None = None

        @init_method
        def init(self, b: InjectableClassB) -> None:
            self.value = b.func()
            self.cls_name = type(self).__name__

    class _ChildClass1(_TestClass):
        @init_method
        def sub_init(self, c: InjectableClassC) -> None:
            self.value = self.value + c.func() if self.value else c.func()

    class _ChildClass2(_TestClass):
        pass

    inject = Injection(Cache())
    inject.add(InjectableClassB, "singleton")
    inject.add(InjectableClassC, "singleton")
    inject.add(_ChildClass1, "singleton")
    inject.add(_ChildClass2, "singleton")

    t1 = inject.require(_ChildClass1)
    t2 = inject.require(_ChildClass2)

    assert t1.value == "bc"
    assert t2.value == "b"
    assert t1.cls_name == _ChildClass1.__name__
    assert t2.cls_name == _ChildClass2.__name__


def test_init_method_call_order() -> None:
    order: list[str] = []

    class _S1:
        @init_method
        def init(self) -> None:
            order.append("s1")

    class _S21:
        @init_method
        def init(self) -> None:
            order.append("s21")

    class _S22:
        @init_method
        def init(self) -> None:
            order.append("s22")

    class _S2(_S21, _S22):
        @init_method
        def init(self) -> None:
            order.append("s2")

    class _Service1(_S1, _S2):
        @init_method
        def init(self) -> None:
            order.append("s")

    class _Service2(_S2, _S1):
        @init_method
        def init(self) -> None:
            order.append("s")

    inject = Injection(Cache())
    inject.add(_Service1, "singleton")
    inject.add(_Service2, "singleton")

    inject.require(_Service1)
    assert order == ["s1", "s21", "s22", "s2", "s"]

    order.clear()

    inject.require(_Service2)
    assert order == ["s21", "s22", "s2", "s1", "s"]


class Service1:
    def __init__(self, s2: "Service2") -> None:
        self.s2 = s2


class Service2:
    def __init__(self, s1: Service1) -> None:
        self.s1 = s1


def test_circular_init_reference() -> None:
    inject = Injection(Cache())
    inject.add(Service1, "singleton")
    inject.add(Service2, "singleton")

    s1 = inject.require(Service1)
    s2 = inject.require(Service2)

    assert s1.s2 is s2
    assert s2.s1 is s1


class Service3:
    def __init__(self, s: "Service3") -> None:
        self.s = s


def test_self_circular_init_reference() -> None:
    inject = Injection(Cache())
    inject.add(Service3, "singleton")

    s = inject.require(Service3)

    assert s.s is s
    assert s.s.s is s


class Service4:
    @init_method
    def init(self, s5: "Service5") -> None:
        pass


class Service5:
    @init_method
    def init(self, s4: Service4) -> None:
        pass


def test_fail_circular_init_method_reference() -> None:
    inject = Injection(Cache())
    inject.add(Service4, "singleton")
    inject.add(Service5, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(Service4)

    assert (
        "Type Service4, A circular call has been detected: "
        "Service4 -> Service4.init -> Service5 -> Service5.init -> Service4" == info.value.message
    )


class Service6:
    @init_method
    def init(self, s8: "Service8") -> None:
        pass


class Service7:
    @init_method
    def init(self, s6: Service6) -> None:
        pass


class Service8:
    @init_method
    def init(self, s7: Service7) -> None:
        pass


def test_fail_three_wide_circular() -> None:
    inject = Injection(Cache())
    inject.add(Service6, "singleton")
    inject.add(Service7, "singleton")
    inject.add(Service8, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(Service8)

    assert (
        "Type Service8, A circular call has been detected: "
        "Service8 -> Service8.init -> Service7 -> Service7.init -> Service6 -> Service6.init -> Service8"
        == info.value.message
    )


def test_arg_resolve_fail_wilcard() -> None:
    def _test_func(a, *args) -> None:
        pass

    inject = Injection(Cache())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, named_args={"a": "a", "b": "b"})

    assert (
        "Callable test_arg_resolve_fail_wilcard.<locals>._test_func, "
        "Positional only parameters and positional wildcards are not allowed" == info.value.message
    )


def test_arg_resolve_fail_positional_only() -> None:
    def _test_func(a, /, b) -> None:
        pass

    inject = Injection(Cache())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, named_args={"a": "a", "b": "b"})

    assert (
        "Callable test_arg_resolve_fail_positional_only.<locals>._test_func, "
        "Positional only parameters and positional wildcards are not allowed" == info.value.message
    )


def test_arg_resolve_fail_too_many_args() -> None:
    def _test_func(a, b) -> None:
        pass

    inject = Injection(Cache())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, args=["a", "b", "c"])

    assert (
        "Callable test_arg_resolve_fail_too_many_args.<locals>._test_func, "
        "Expected 2 arguments, 3 given" == info.value.message
    )


def test_arg_resolve() -> None:
    def _test_func(a, b, c: InjectableClassC, d="d", **kwargs) -> None:
        assert a == "a"
        assert b == "b"
        assert c.func() == "c"
        assert d == "d"
        assert kwargs == {"e": "e", "f": "f"}

    inject = Injection(Cache())
    inject.add(InjectableClassC, "singleton")

    inject.call(
        _test_func,
        args=["a"],
        named_args={"b": "b", "e": "e", "f": "f"},
    )


def test_two_injections() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    class _C3:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    inject = Injection(Cache())
    inject.add(_C1, "singleton")
    inject.add(_C2, "singleton")
    inject.add(_C3, "singleton")

    c2 = inject.require(_C2)
    c3 = inject.require(_C3)

    assert c2.c1 is c3.c1


def test_transient_injection() -> None:
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

    inject = Injection(Cache())
    inject.add(_C1, "transient")
    inject.add(_C2, "singleton")
    inject.add(_C3, "singleton")
    inject.add(_C4, "singleton")

    c3 = inject.require(_C3)
    c4 = inject.require(_C4)

    assert c3.c2 is c4.c2
    assert c3.c1 is not c4.c1


def test_scoped_injection_fail_no_scope() -> None:
    class _C1:
        pass

    inject = Injection(Cache())
    inject.add(_C1, "scoped")

    with pytest.raises(InjectionError) as info:
        inject.require(_C1)

    assert (
        "Injection strategy for test_scoped_injection_fail_no_scope.<locals>._C1 "
        "must be singleton or transient to be required in this context" == info.value.message
    )


def test_scoped_injection_fail_no_scope_in_func() -> None:
    class _C1:
        pass

    def _func(c1: _C1) -> None:
        pass

    inject = Injection(Cache())
    inject.add(_C1, "scoped")

    with pytest.raises(InjectionError) as info:
        inject.call(_func)

    assert (
        "Callable test_scoped_injection_fail_no_scope_in_func.<locals>._func, Parameter 'c1', "
        "Cannot instantiate a scoped service in a singleton service" == info.value.message
    )


def test_scoped_injection_fail_no_scope_in_singleton() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_C1, "scoped")
    inject.add(_C2, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_C2)

    assert (
        "Callable test_scoped_injection_fail_no_scope_in_singleton.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a singleton service" == info.value.message
    )


def test_scoped_injection_fail_no_scope_in_transient() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_C1, "scoped")
    inject.add(_C2, "transient")

    with pytest.raises(InjectionError) as info:
        inject.require(_C2)

    assert (
        "Callable test_scoped_injection_fail_no_scope_in_transient.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a transient service" == info.value.message
    )


def test_fail_get_scoped_from_singleton_in_scope() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_C1, "scoped")
    inject.add(_C2, "singleton")

    sub_inject = inject.get_scoped_session()

    with pytest.raises(InjectionError) as info:
        sub_inject.require(_C2)

    assert (
        "Callable test_fail_get_scoped_from_singleton_in_scope.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a singleton service" == info.value.message
    )


def test_fail_get_scoped_from_transient_in_scope() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_C1, "scoped")
    inject.add(_C2, "transient")

    sub_inject = inject.get_scoped_session()

    with pytest.raises(InjectionError) as info:
        sub_inject.require(_C2)

    assert (
        "Callable test_fail_get_scoped_from_transient_in_scope.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a transient service" == info.value.message
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

    inject = Injection(Cache())
    inject.add(_C1, "transient")
    inject.add(_C2, "singleton")
    inject.add(_C3, "scoped")
    inject.add(_C4, "scoped")
    inject.add(_C5, "scoped")

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


def test_get_injection_scoped_context() -> None:
    inject = Injection(Cache())
    sub_inject1 = inject.get_scoped_session()
    sub_inject2 = inject.get_scoped_session()

    assert inject.require(Injection) is inject
    assert sub_inject1.require(Injection) is sub_inject1
    assert sub_inject2.require(Injection) is sub_inject2


def test_require_transient_service() -> None:
    class _C1:
        pass

    class _C2:
        pass

    inject = Injection(Cache())
    inject.add(_C1, "transient")
    inject.add(_C2, "singleton")

    assert inject.require(_C1) is not inject.require(_C1)
    assert inject.require(_C2) is inject.require(_C2)


def test_inject_nullable() -> None:
    class _TestClass:
        def __init__(self, sub: _SubTestClass | None, i: int | None) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None
    assert t.i is None


def test_inject_nullable_bis() -> None:
    class _TestClass:
        def __init__(self, sub: _SubTestClass | None) -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_inject_with_default() -> None:
    s = _SubTestClass()

    class _TestClass:
        def __init__(self, sub: _SubTestClass = s, i: int = 3) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is s
    assert t.i == 3


def test_inject_no_union() -> None:
    class _TestClass:
        def __init__(self, v: int | bool) -> None:
            self.v = v

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        "Callable test_inject_no_union.<locals>._TestClass, Parameter 'v', "
        "Type unions are not allowed" == info.value.message
    )


def test_optional_type_literal_right() -> None:
    class _TestClass:
        def __init__(self, sub: "_SubTestClass | None") -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_optional_type_literal_left() -> None:
    class _TestClass:
        def __init__(self, sub: "None | _SubTestClass") -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_optional_type_literal_bis() -> None:
    class _TestClass:
        def __init__(self, sub: "_SubTestClass | None") -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_generic_injection() -> None:
    _T = TypeVar("_T")

    class _GenericTest[T]:
        pass

    class _ParamClass:
        pass

    inject = Injection(Cache())
    inject.add(_GenericTest[_ParamClass], "singleton")

    g = inject.require(_GenericTest[_ParamClass])

    assert meta.has(g, GenericMeta)
    assert meta.get(g, GenericMeta) == (_ParamClass,)


def test_generic_injection_from_cache() -> None:
    class _GenericTest[T]:
        pass

    class _ParamClass:
        pass

    cache = Cache()

    injectable(cache=cache)(_GenericTest[_ParamClass])

    inject = Injection(cache)

    g = inject.require(_GenericTest[_ParamClass])

    assert meta.has(g, GenericMeta)
    assert meta.get(g, GenericMeta) == (_ParamClass,)


def test_generic_no_direct_injection_literal() -> None:
    class _GenericTest[T]:
        pass

    inject = Injection(Cache())

    with pytest.raises(TypingError) as info:
        inject.add(_GenericTest["_SubTestClass"], "singleton")

    assert (
        "Type test_generic_no_direct_injection_literal.<locals>._GenericTest, "
        "Generic parameter '_SubTestClass' cannot be a string" == info.value.message
    )


def test_generic_sub_injection() -> None:
    class _GenericTest[_T]:
        pass

    class _ParamClass:
        pass

    class _TestClass:
        def __init__(self, g: _GenericTest[_ParamClass]) -> None:
            self.g = g

    inject = Injection(Cache())
    inject.add(_GenericTest[_ParamClass], "singleton")
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert meta.has(t.g, GenericMeta)
    assert meta.get(t.g, GenericMeta) == (_ParamClass,)


def test_generic_sub_injection_literal() -> None:
    class _GenericTest[T]:
        pass

    class _TestClass:
        def __init__(self, g: _GenericTest["_SubTestClass"]) -> None:
            self.g = g

    inject = Injection(Cache())
    inject.add(_GenericTest[_SubTestClass], "singleton")
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert meta.has(t.g, GenericMeta)
    assert meta.get(t.g, GenericMeta) == (_SubTestClass,)


def test_require_decorator() -> None:
    class _ParamClass:
        def __init__(self) -> None:
            self.v = 1

    class _TestClass:
        def __init__(self) -> None:
            pass

        @require(_ParamClass)
        def param(self):
            pass

    inject = Injection(Cache())
    inject.add(_ParamClass, "singleton")
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.param.v == 1


def test_instantiate_type() -> None:
    calls: list[str] = []

    class _Service:
        def __init__(self) -> None:
            calls.append("__init__")

        @init_method
        def _init(self) -> None:
            calls.append("_init")

    inject = Injection(Cache())

    service = inject.instantiate(_Service)

    assert isinstance(service, _Service)
    assert calls == ["__init__", "_init"]


def test_fail_immediate_instantiate() -> None:
    class _TestClass:
        pass

    inject = Injection(Cache())

    with pytest.raises(InjectionError) as info:
        inject.add(
            _TestClass,
            "singleton",
            instance=_TestClass(),
            instantiate=True,
        )

    assert f"Cannot instantiate {_TestClass} if an instance is provided" == info.value.message


def test_register_with_super_type() -> None:
    class _Service[T]:
        pass

    class _User:
        pass

    class _Role:
        pass

    class _UserService(_Service[_User]):
        pass

    class _RoleService(_Service[_Role]):
        pass

    inject = Injection(Cache())
    inject.add(_UserService, "singleton", super_cls=_Service[_User])
    inject.add(_RoleService, "singleton", super_cls=_Service[_Role])

    us = inject.require(_Service[_User])
    assert isinstance(us, _UserService)

    rs = inject.require(_Service[_Role])
    assert isinstance(rs, _RoleService)


def test_register_with_super_type_complete() -> None:
    class _Service[T]:
        pass

    class _User:
        pass

    class _Role:
        pass

    class _UserService(_Service[_User]):
        pass

    class _RoleService(_Service[_Role]):
        pass

    inject = Injection(Cache())
    inject.add(_UserService, "singleton")
    inject.add(_RoleService, "singleton")
    inject.add(_UserService, "singleton", super_cls=_Service[_User])
    inject.add(_RoleService, "singleton", super_cls=_Service[_Role])

    us1 = inject.require(_UserService)
    assert isinstance(us1, _UserService)

    rs1 = inject.require(_RoleService)
    assert isinstance(rs1, _RoleService)

    us2 = inject.require(_Service[_User])
    assert isinstance(us2, _UserService)
    assert us1 is us2

    rs2 = inject.require(_Service[_Role])
    assert isinstance(rs2, _RoleService)
    assert rs1 is rs2


def test_register_match_all() -> None:
    class _ServiceA:
        pass

    class _ServiceB:
        pass

    class _Logger[T]:
        pass

    class _LoggerA(_Logger[_ServiceA]):
        pass

    inject = Injection(Cache())
    inject.add(_Logger[Any], "singleton", match_all=True)
    inject.add(_LoggerA, "singleton", super_cls=_Logger[_ServiceA])

    _logger_a = inject.require(_Logger[_ServiceA])
    _logger_b = inject.require(_Logger[_ServiceB])

    assert isinstance(_logger_a, _Logger)
    assert isinstance(_logger_a, _LoggerA)
    assert meta.get(_logger_a, GenericMeta) == (_ServiceA,)

    assert isinstance(_logger_b, _Logger)
    assert not isinstance(_logger_b, _LoggerA)
    assert meta.get(_logger_b, GenericMeta) == (_ServiceB,)


def test_require_from_typevar() -> None:
    class _Resource:
        pass

    class _SpecificResource(_Resource):
        pass

    class _Service[TS: _Resource]:
        pass

    class _SpecificService(_Service[_SpecificResource]):
        pass

    class _Controller[TC: _Resource]:
        def __init__(self, sub: _Service[TC]) -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add(_Service[_Resource], "singleton")
    inject.add(_SpecificService, "singleton", super_cls=_Service[_SpecificResource])

    inject.add(_Controller[_Resource], "singleton")
    inject.add(_Controller[_SpecificResource], "singleton")

    ctrl = inject.require(_Controller[_Resource])
    assert isinstance(ctrl.sub, _Service)
    assert meta.get(ctrl.sub, GenericMeta) == (_Resource,)

    ctrl2 = inject.require(_Controller[_SpecificResource])
    assert isinstance(ctrl2.sub, _SpecificService)
    assert meta.get(ctrl2.sub, GenericMeta) == (_SpecificResource,)


def test_init_method_with_typevar() -> None:
    class _Entity:
        pass

    class _Service[T: _Entity]:
        pass

    class _Controller[T: _Entity]:
        @init_method
        def init(self, s: _Service[T]) -> None:
            self.s = s  # pyright: ignore

    inject = Injection(Cache())
    inject.add(_Service[_Entity], "singleton")
    inject.add(_Controller[_Entity], "singleton")

    ctrl = inject.require(_Controller[_Entity])

    assert isinstance(ctrl.s, _Service)
    assert meta.get(ctrl.s, GenericMeta) == (_Entity,)


def test_fail_require_from_typevar_non_generic_parent() -> None:
    class _Entity:
        pass

    class _Service[T: _Entity]:
        pass

    _T = TypeVar("_T", bound=_Entity)

    class _Controller:
        def __init__(self, s: _Service[_T]) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_Service[_Entity], "singleton")
    inject.add(_Controller, "singleton")

    with pytest.raises(TypingError) as info:
        inject.require(_Controller)

    assert (
        "Type test_fail_require_from_typevar_non_generic_parent.<locals>._Service, "
        "TypeVar ~_T could not be found in lookup" == info.value.message
    )


def test_fail_require_from_typevar_different_names() -> None:
    class _Entity1:
        pass

    class _Entity2:
        pass

    _T1 = TypeVar("_T1", bound=_Entity1)
    _T2 = TypeVar("_T2", bound=_Entity2)

    class _Service[_T1: _Entity1]:
        pass

    class _Controller[_T2: _Entity2]:
        def __init__(self, s: _Service[_T1]) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_Service[_Entity1], "singleton")
    inject.add(_Controller[_Entity2], "singleton")

    with pytest.raises(TypingError) as info:
        inject.require(_Controller[_Entity2])

    assert (
        "Type test_fail_require_from_typevar_different_names.<locals>._Service, "
        "TypeVar ~_T1 could not be found in lookup" == info.value.message
    )


def test_arg_resolver() -> None:
    cache = Cache()

    class _Service:
        pass

    class _Controller:
        def __init__(self, s: _Service) -> None:
            self.s = s

    _s = _Service()
    order: list[int] = []

    class _Resolver2:
        def supports(self, options: ArgResolverOptions):
            order.append(3)
            return True

        def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
            order.append(4)
            return (options.name, _s)

    class _Resolver1:
        def supports(self, options: ArgResolverOptions):
            order.append(1)
            return False

        def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
            order.append(2)
            return ("", 0)

    injection_arg_resolver(priority=2, cache=cache)(_Resolver2)
    injection_arg_resolver(priority=1, cache=cache)(_Resolver1)

    inject = Injection(cache)
    inject.add(_Controller, "singleton")

    ctrl = inject.require(_Controller)

    assert order == [1, 3, 4]
    assert ctrl.s is _s


def test_service_in_arg_resolver() -> None:
    cache = Cache()

    class _Service:
        pass

    class _Controller:
        pass

    order: list[_Service] = []

    class _Resolver:
        def __init__(self, s: _Service) -> None:
            order.append(s)

        def supports(self, options: ArgResolverOptions):
            return False

        def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
            ...

    injection_arg_resolver(priority=1, cache=cache, scoped=True)(_Resolver)

    inject = Injection(cache)
    inject.add(_Service, "singleton")
    inject.add(_Controller, "singleton")

    scoped = inject.get_scoped_session()

    scoped.require(_Controller)

    assert len(order) == 1
    assert isinstance(order[0], _Service)


def test_before_after_init() -> None:
    cache = Cache()

    order: list[tuple[str, object]] = []

    class _Service:
        @init_method
        def _init(self) -> None:
            order.append(("init", self))

    def _before(s: _Service) -> None:
        order.append(("before", s))

    def _after(s: _Service) -> None:
        order.append(("after", s))

    inject = Injection(cache)
    inject.add(_Service, "singleton", before_init=[_before], after_init=[_after])

    _s = inject.require(_Service)

    assert order == [("before", _s), ("init", _s), ("after", _s)]


def test_context_manager() -> None:
    cache = Cache()

    check: list[str] = []

    class Service:
        def __enter__(self) -> Self:
            check.append("enter")
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
            /,
        ) -> None:
            check.append("exit")

    with Injection(cache) as inject:
        inject.add(Service, "singleton")
        inject.require(Service)
        assert check == ["enter"]
    assert check == ["enter", "exit"]


def test_context_manager_subinject() -> None:
    cache = Cache()

    check: list[str] = []

    class Service1:
        def __enter__(self) -> Self:
            check.append("enter1")
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
            /,
        ) -> None:
            check.append("exit1")

    class Service2:
        def __enter__(self) -> Self:
            check.append("enter2")
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
            /,
        ) -> None:
            check.append("exit2")

    with Injection(cache) as inject:
        inject.add(Service1, "singleton")
        inject.add(Service2, "scoped")
        inject.require(Service1)
        assert check == ["enter1"]
        with inject.get_scoped_session() as subinject:
            subinject.require(Service2)
            assert check == ["enter1", "enter2"]
        assert check == ["enter1", "enter2", "exit2"]
    assert check == ["enter1", "enter2", "exit2", "exit1"]
