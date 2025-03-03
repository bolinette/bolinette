# pyright: reportMissingParameterType=false, reportUnknownParameterType=false, reportUnknownArgumentType=false
from types import TracebackType
from typing import Any, Protocol, Self, TypeVar

import pytest

from bolinette.core import Cache
from bolinette.core.exceptions import InjectionError, TypingError, UnregisteredTypeError
from bolinette.core.injection import Injection, after_init, before_init, injectable, post_init, require
from bolinette.core.injection.resolver import ArgResolverOptions, injection_arg_resolver
from bolinette.core.types.type import Type


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


def test_register_singleton_with_interface() -> None:
    class ServiceProto(Protocol): ...

    class Service: ...

    inject = Injection(Cache())
    inject.add_singleton(ServiceProto, Service)

    assert ServiceProto in inject.registered_types


def test_register_singleton_no_interface() -> None:
    class Service: ...

    inject = Injection(Cache())
    inject.add_singleton(Service)

    assert Service in inject.registered_types


def test_register_transient_with_interface() -> None:
    class ServiceProto(Protocol): ...

    class Service: ...

    inject = Injection(Cache())
    inject.add_transient(ServiceProto, Service)

    assert ServiceProto in inject.registered_types


def test_register_transient_no_interface() -> None:
    class Service: ...

    inject = Injection(Cache())
    inject.add_transient(Service)

    assert Service in inject.registered_types


def test_require_singleton() -> None:
    class Service: ...

    inject = Injection(Cache())
    inject.add_singleton(Service)

    service = inject.require(Service)
    assert isinstance(service, Service)

    service2 = inject.require(Service)
    assert service is service2


def test_require_transient() -> None:
    class Service: ...

    inject = Injection(Cache())
    inject.add_transient(Service)

    service = inject.require(Service)
    assert isinstance(service, Service)

    service2 = inject.require(Service)
    assert service is not service2


def test_require_singleton_with_param() -> None:
    class SubService: ...

    class Service:
        def __init__(self, sub: SubService) -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add_singleton(Service)
    inject.add_singleton(SubService)

    service = inject.require(Service)

    assert isinstance(service, Service)
    assert isinstance(service.sub, SubService)


def test_class_injection() -> None:
    inject = Injection(Cache())
    inject.add_singleton(InjectableClassA)
    inject.add_singleton(InjectableClassB)
    inject.add_singleton(InjectableClassC)
    inject.add_singleton(InjectableClassD)

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
    inject.add_singleton(InjectableClassA)
    inject.add_singleton(InjectableClassB)
    inject.add_singleton(InjectableClassC)
    inject.add_singleton(InjectableClassD)

    inject.call(_test_func)


async def test_inject_call_async() -> None:
    async def _test_func(b: InjectableClassB) -> None:
        assert b.func() == "b"

    inject = Injection(Cache())
    inject.add_singleton(InjectableClassB)

    await inject.call(_test_func)


async def test_fail_injection() -> None:
    inject = Injection(Cache())
    inject.add_singleton(InjectableClassB)

    with pytest.raises(UnregisteredTypeError) as info:
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
    inject.add_singleton(InjectableClassD)

    d = inject.require(InjectableClassD)
    with pytest.raises(InjectionError) as info:
        d.c.func()

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
            self.sub = sub

    inject = Injection(Cache())
    inject.add_singleton(_Service)

    s = inject.require(_Service)
    with pytest.raises(InjectionError) as info:
        print(s.sub)

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
    inject.add_singleton(InjectableClassB)

    b1 = inject.require(InjectableClassB)
    b2 = inject.require(InjectableClassB)

    assert b1 is b2


def test_add_instance_no_singleton() -> None:
    inject = Injection(Cache())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add_transient(InjectableClassB, instance=b)

    assert "Injection strategy for InjectableClassB must be singleton if an instance is provided" == info.value.message


def test_add_instance() -> None:
    inject = Injection(Cache())

    b = InjectableClassB()

    inject.add_singleton(InjectableClassB, instance=b)

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
    inject.add_singleton(_TestClass)

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
    inject.add_singleton(_TestClass)

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert (
        "Callable test_no_annotation.<locals>._TestClass, Parameter '_1', Annotation is required" == info.value.message
    )


def test_use_post_init() -> None:
    class _TestClass:
        def __init__(self) -> None:
            self.value: str | None = None
            self.cls_name: str | None = None

        @post_init
        def init(self, b: InjectableClassB) -> None:
            self.value = b.func()
            self.cls_name = type(self).__name__

    class _ChildClass1(_TestClass):
        @post_init
        def sub_init(self, c: InjectableClassC) -> None:
            self.value = self.value + c.func() if self.value else c.func()

    class _ChildClass2(_TestClass):
        pass

    inject = Injection(Cache())
    inject.add_singleton(InjectableClassB)
    inject.add_singleton(InjectableClassC)
    inject.add_singleton(_ChildClass1)
    inject.add_singleton(_ChildClass2)

    t1 = inject.require(_ChildClass1)
    t2 = inject.require(_ChildClass2)

    assert t1.value == "bc"
    assert t2.value == "b"
    assert t1.cls_name == _ChildClass1.__name__
    assert t2.cls_name == _ChildClass2.__name__


def test_post_init_call_order() -> None:
    order: list[str] = []

    class _S1:
        @post_init
        def init(self) -> None:
            order.append("s1")

    class _S21:
        @post_init
        def init(self) -> None:
            order.append("s21")

    class _S22:
        @post_init
        def init(self) -> None:
            order.append("s22")

    class _S2(_S21, _S22):
        @post_init
        def init(self) -> None:
            order.append("s2")

    class _Service1(_S1, _S2):
        @post_init
        def init(self) -> None:
            order.append("s")

    class _Service2(_S2, _S1):
        @post_init
        def init(self) -> None:
            order.append("s")

    inject = Injection(Cache())
    inject.add_singleton(_Service1)
    inject.add_singleton(_Service2)

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
    inject.add_singleton(Service1)
    inject.add_singleton(Service2)

    s1 = inject.require(Service1)
    s2 = inject.require(Service2)

    assert s1.s2 is s2
    assert s2.s1 is s1


class Service3:
    def __init__(self, s: "Service3") -> None:
        self.s = s


def test_self_circular_init_reference() -> None:
    inject = Injection(Cache())
    inject.add_singleton(Service3)

    s = inject.require(Service3)

    assert s.s is s
    assert s.s.s is s


class Service4:
    @post_init
    def init(self, s5: "Service5") -> None:
        pass


class Service5:
    @post_init
    def init(self, s4: Service4) -> None:
        pass


def test_fail_circular_post_init_reference() -> None:
    inject = Injection(Cache())
    inject.add_singleton(Service4)
    inject.add_singleton(Service5)

    with pytest.raises(InjectionError) as info:
        inject.require(Service4)

    assert (
        "Type Service4, A circular call has been detected: "
        "Service4 -> Service4.init -> Service5 -> Service5.init -> Service4" == info.value.message
    )


class Service6:
    @post_init
    def init(self, s8: "Service8") -> None:
        pass


class Service7:
    @post_init
    def init(self, s6: Service6) -> None:
        pass


class Service8:
    @post_init
    def init(self, s7: Service7) -> None:
        pass


def test_fail_three_wide_circular() -> None:
    inject = Injection(Cache())
    inject.add_singleton(Service6)
    inject.add_singleton(Service7)
    inject.add_singleton(Service8)

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
    inject.add_singleton(InjectableClassC)

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
    inject.add_singleton(_C1)
    inject.add_singleton(_C2)
    inject.add_singleton(_C3)

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
    inject.add_transient(_C1)
    inject.add_singleton(_C2)
    inject.add_singleton(_C3)
    inject.add_singleton(_C4)

    c3 = inject.require(_C3)
    c4 = inject.require(_C4)

    assert c3.c2 is c4.c2
    assert c3.c1 is not c4.c1


def test_scoped_injection_fail_no_scope() -> None:
    class _C1:
        pass

    inject = Injection(Cache())
    inject.add_scoped(_C1)

    with pytest.raises(InjectionError) as info:
        inject.require(_C1)

    assert (
        "Cannot instantiate scoped service test_scoped_injection_fail_no_scope.<locals>._C1 "
        "from a non scoped injection context" == info.value.message
    )


def test_scoped_injection_fail_no_scope_in_func() -> None:
    class _C1:
        pass

    def _func(c1: _C1) -> None:
        pass

    inject = Injection(Cache())
    inject.add_scoped(_C1)

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
            self.c1 = c1

    inject = Injection(Cache())
    inject.add_scoped(_C1)
    inject.add_singleton(_C2)

    c2 = inject.require(_C2)
    with pytest.raises(InjectionError) as info:
        print(c2.c1)

    assert (
        "Callable test_scoped_injection_fail_no_scope_in_singleton.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a singleton service" == info.value.message
    )


def test_scoped_injection_fail_no_scope_in_transient() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    inject = Injection(Cache())
    inject.add_scoped(_C1)
    inject.add_transient(_C2)

    c2 = inject.require(_C2)
    with pytest.raises(InjectionError) as info:
        print(c2.c1)

    assert (
        "Callable test_scoped_injection_fail_no_scope_in_transient.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a transient service" == info.value.message
    )


def test_fail_get_scoped_from_singleton_in_scope() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    inject = Injection(Cache())
    inject.add_scoped(_C1)
    inject.add_singleton(_C2)

    sub_inject = inject.get_scoped_session()

    c2 = sub_inject.require(_C2)
    with pytest.raises(InjectionError) as info:
        print(c2.c1)

    assert (
        "Callable test_fail_get_scoped_from_singleton_in_scope.<locals>._C2, Parameter 'c1', "
        "Cannot instantiate a scoped service in a singleton service" == info.value.message
    )


def test_fail_get_scoped_from_transient_in_scope() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    inject = Injection(Cache())
    inject.add_scoped(_C1)
    inject.add_transient(_C2)

    sub_inject = inject.get_scoped_session()

    c2 = sub_inject.require(_C2)
    with pytest.raises(InjectionError) as info:
        print(c2.c1)

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
    inject.add_transient(_C1)
    inject.add_singleton(_C2)
    inject.add_scoped(_C3)
    inject.add_scoped(_C4)
    inject.add_scoped(_C5)

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
    inject.add_transient(_C1)
    inject.add_singleton(_C2)

    assert inject.require(_C1) is not inject.require(_C1)
    assert inject.require(_C2) is inject.require(_C2)


def test_inject_nullable() -> None:
    class _TestClass:
        def __init__(self, sub: _SubTestClass | None, i: int | None) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache())
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.sub is None
    assert t.i is None


def test_inject_nullable_bis() -> None:
    class _TestClass:
        def __init__(self, sub: _SubTestClass | None) -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.sub is None


def test_inject_with_default() -> None:
    s = _SubTestClass()

    class _TestClass:
        def __init__(self, sub: _SubTestClass = s, i: int = 3) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache())
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.sub is s
    assert t.i == 3


def test_inject_no_union() -> None:
    class _TestClass:
        def __init__(self, v: int | bool) -> None:
            self.v = v

    inject = Injection(Cache())
    inject.add_singleton(_TestClass)

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
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.sub is None


def test_optional_type_literal_left() -> None:
    class _TestClass:
        def __init__(self, sub: "None | _SubTestClass") -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.sub is None


def test_optional_type_literal_bis() -> None:
    class _TestClass:
        def __init__(self, sub: "_SubTestClass | None") -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.sub is None


def test_generic_injection() -> None:
    _T = TypeVar("_T")

    class _GenericTest[T]:
        def __init__(self, cls: type[T]) -> None:
            self.cls = cls

    class _ParamClass:
        pass

    inject = Injection(Cache())
    inject.add_singleton(_GenericTest[_ParamClass])

    g = inject.require(_GenericTest[_ParamClass])

    assert isinstance(g, _GenericTest)
    assert g.cls is _ParamClass


def test_generic_injection_from_cache() -> None:
    class _GenericTest[T]:
        def __init__(self, cls: type[T]) -> None:
            self.cls = cls

    class _ParamClass:
        pass

    cache = Cache()

    injectable(cache=cache)(_GenericTest[_ParamClass])

    inject = Injection(cache)

    g = inject.require(_GenericTest[_ParamClass])

    assert isinstance(g, _GenericTest)
    assert g.cls is _ParamClass


def test_generic_no_direct_injection_literal() -> None:
    class _GenericTest[T]:
        pass

    inject = Injection(Cache())

    with pytest.raises(TypingError) as info:
        inject.add_singleton(_GenericTest["_SubTestClass"])

    assert (
        "Type test_generic_no_direct_injection_literal.<locals>._GenericTest, "
        "Generic parameter '_SubTestClass' cannot be a string" == info.value.message
    )


def test_generic_sub_injection() -> None:
    class _GenericTest[T]:
        def __init__(self, cls: type[T]) -> None:
            self.cls = cls

    class _ParamClass:
        pass

    class _TestClass:
        def __init__(self, g: _GenericTest[_ParamClass]) -> None:
            self.g = g

    inject = Injection(Cache())
    inject.add_singleton(_GenericTest[_ParamClass])
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert isinstance(t.g, _GenericTest)
    assert t.g.cls is _ParamClass


def test_generic_sub_injection_literal() -> None:
    class _GenericTest[T]:
        def __init__(self, cls: type[T]) -> None:
            self.cls = cls

    class _TestClass:
        def __init__(self, g: _GenericTest["_SubTestClass"]) -> None:
            self.g = g

    inject = Injection(Cache())
    inject.add_singleton(_GenericTest[_SubTestClass])
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert isinstance(t.g, _GenericTest)
    assert t.g.cls is _SubTestClass


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
    inject.add_singleton(_ParamClass)
    inject.add_singleton(_TestClass)

    t = inject.require(_TestClass)

    assert t.param.v == 1


def test_instantiate_type() -> None:
    calls: list[str] = []

    class _Service:
        def __init__(self) -> None:
            calls.append("__init__")

        @post_init
        def _init(self) -> None:
            calls.append("_init")

    inject = Injection(Cache())

    service = inject.instantiate(_Service)

    assert isinstance(service, _Service)
    assert calls == ["__init__", "_init"]


def test_register_with_interface_type() -> None:
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
    inject.add_singleton(_Service[_User], _UserService)
    inject.add_singleton(_Service[_Role], _RoleService)

    us = inject.require(_Service[_User])
    assert isinstance(us, _UserService)
    assert not inject.is_registered(_UserService)

    rs = inject.require(_Service[_Role])
    assert isinstance(rs, _RoleService)
    assert not inject.is_registered(_RoleService)


def test_register_with_interface_type_complete() -> None:
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
    inject.add_singleton(_UserService)
    inject.add_singleton(_RoleService)
    inject.add_singleton(_Service[_User], _UserService)
    inject.add_singleton(_Service[_Role], _RoleService)

    us1 = inject.require(_UserService)
    assert isinstance(us1, _UserService)

    us2 = inject.require(_Service[_User])
    assert isinstance(us2, _UserService)
    assert us1 is us2

    rs1 = inject.require(_RoleService)
    assert isinstance(rs1, _RoleService)

    rs2 = inject.require(_Service[_Role])
    assert isinstance(rs2, _RoleService)
    assert rs1 is rs2


def test_register_with_interface_type_with_decorator() -> None:
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

    cache = Cache()
    injectable(cache=cache, interfaces=[_Service[_User]])(_UserService)
    injectable(cache=cache, interfaces=[_Service[_Role]])(_RoleService)

    inject = Injection(cache)

    assert inject.is_registered(_Service[_User])
    assert inject.is_registered(_UserService)
    us = inject.require(_Service[_User])
    assert isinstance(us, _UserService)

    assert inject.is_registered(_Service[_Role])
    assert inject.is_registered(_RoleService)
    rs = inject.require(_Service[_Role])
    assert isinstance(rs, _RoleService)


def test_register_match_all() -> None:
    class _ServiceA:
        pass

    class _ServiceB:
        pass

    class _Logger[T]:
        def __init__(self, s: T) -> None:
            self.s = s

    class _LoggerA(_Logger[_ServiceA]):
        pass

    inject = Injection(Cache())
    inject.add_singleton(_ServiceA)
    inject.add_singleton(_ServiceB)
    inject.add_singleton(_Logger[Any], match_all=True)
    inject.add_singleton(_Logger[_ServiceA], _LoggerA)

    _logger_a = inject.require(_Logger[_ServiceA])
    assert isinstance(_logger_a, _Logger)
    assert isinstance(_logger_a, _LoggerA)
    assert isinstance(_logger_a.s, _ServiceA)

    _logger_b = inject.require(_Logger[_ServiceB])
    assert isinstance(_logger_b, _Logger)
    assert not isinstance(_logger_b, _LoggerA)
    assert isinstance(_logger_b.s, _ServiceB)


def test_require_from_typevar() -> None:
    class _Resource:
        pass

    class _SpecificResource(_Resource):
        pass

    class _Service[TS: _Resource]:
        def __init__(self, res: TS) -> None:
            self.res = res

    class _SpecificService(_Service[_SpecificResource]):
        pass

    class _Controller[TC: _Resource]:
        def __init__(self, sub: _Service[TC]) -> None:
            self.sub = sub

    inject = Injection(Cache())
    inject.add_singleton(_Resource)
    inject.add_singleton(_SpecificResource)
    inject.add_singleton(_Service[_Resource])
    inject.add_singleton(_Service[_SpecificResource], _SpecificService)
    inject.add_singleton(_Controller[_Resource])
    inject.add_singleton(_Controller[_SpecificResource])

    ctrl = inject.require(_Controller[_Resource])
    assert isinstance(ctrl.sub, _Service)
    assert isinstance(ctrl.sub.res, _Resource)

    ctrl2 = inject.require(_Controller[_SpecificResource])
    assert isinstance(ctrl2.sub, _SpecificService)
    assert isinstance(ctrl2.sub.res, _SpecificResource)


def test_post_init_with_typevar() -> None:
    class _Entity:
        pass

    class _Service[T: _Entity]:
        def __init__(self, e: type[T]) -> None:
            self.e = e

    class _Controller[T: _Entity]:
        @post_init
        def init(self, s: _Service[T]) -> None:
            self.s = s  # pyright: ignore

    inject = Injection(Cache())
    inject.add_singleton(_Service[_Entity])
    inject.add_singleton(_Controller[_Entity])

    ctrl = inject.require(_Controller[_Entity])

    assert isinstance(ctrl.s, _Service)
    assert ctrl.s.e is _Entity


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
    inject.add_singleton(_Service[_Entity])
    inject.add_singleton(_Controller)

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
    inject.add_singleton(_Service[_Entity1])
    inject.add_singleton(_Controller[_Entity2])

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

    class ServiceResolver:
        def supports(self, options: ArgResolverOptions):
            order.append(1)
            return options.t.cls is _Service

        def resolve(self, options: ArgResolverOptions) -> Any:
            order.append(2)
            return _s

    injection_arg_resolver(cache=cache)(ServiceResolver)

    inject = Injection(cache)
    inject.add_singleton(_Controller)

    ctrl = inject.require(_Controller)
    ctrl_service = ctrl.s

    assert order == [1, 2]
    assert ctrl_service is _s


def test_service_in_arg_resolver() -> None:
    cache = Cache()

    class _Service:
        pass

    class _Config:
        pass

    class _Controller:
        def __init__(self, s: _Service) -> None:
            self.s = s

    order: list[_Config] = []

    class _Resolver:
        def __init__(self, c: _Config) -> None:
            self.c = c

        def supports(self, options: ArgResolverOptions) -> bool:
            order.append(self.c)
            return options.t.cls is _Service

        def resolve(self, options: ArgResolverOptions) -> Any:
            return _Service()

    injection_arg_resolver(priority=1, cache=cache, scoped=True)(_Resolver)

    inject = Injection(cache)
    inject.add_singleton(_Config)
    inject.add_singleton(_Controller)

    scoped = inject.get_scoped_session()

    _ = scoped.require(_Controller).s

    assert len(order) == 1
    assert isinstance(order[0], _Config)


def test_before_after_init() -> None:
    cache = Cache()

    order: list[tuple[str, object]] = []

    class _Service:
        @post_init
        def _init(self) -> None:
            order.append(("init", self))

    def _before(s: _Service) -> None:
        order.append(("before", s))

    def _after(s: _Service) -> None:
        order.append(("after", s))

    inject = Injection(cache)
    inject.add_singleton(_Service, options={"before_init": [_before], "after_init": [_after]})

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
        inject.add_singleton(Service)
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
        inject.add_singleton(Service1)
        inject.add_scoped(Service2)
        inject.require(Service1)
        assert check == ["enter1"]
        with inject.get_scoped_session() as subinject:
            subinject.require(Service2)
            assert check == ["enter1", "enter2"]
        assert check == ["enter1", "enter2", "exit2"]
    assert check == ["enter1", "enter2", "exit2", "exit1"]


async def test_async_context_manager_subinject() -> None:
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
        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
            /,
        ) -> None:
            check.append("exit2")

    with Injection(cache) as inject:
        inject.add_singleton(Service1)
        inject.add_scoped(Service2)
        inject.require(Service1)
        assert check == ["enter1"]
        async with inject.get_async_scoped_session() as subinject:
            subinject.require(Service2)
            assert check == ["enter1"]
        assert check == ["enter1", "exit2"]
    assert check == ["enter1", "exit2", "exit1"]


def test_inject_generic_type_in_init() -> None:
    class Service[A, B]:
        def __init__(self, ca: type[A], ta: Type[A], cb: type[B], tb: Type[B]) -> None:
            self.ca = ca
            self.ta = ta
            self.cb = cb
            self.tb = tb

    cache = Cache()
    inject = Injection(cache)
    inject.add_singleton(Service[int, str])

    s = inject.require(Service[int, str])

    assert s.ca is int
    assert s.ta == Type(int)
    assert s.cb is str
    assert s.tb == Type(str)


def test_resolve_typevar_in_super_class_init() -> None:
    data: list[Type[Any]] = []

    class Service[T]:
        @post_init
        def init(self, t: Type[T]) -> None:
            data.append(t)

    class IntService(Service[int]):
        pass

    cache = Cache()
    inject = Injection(cache)
    inject.add_singleton(IntService)
    inject.require(IntService)

    assert data == [Type(int)]


def test_before_and_after_init() -> None:
    cache = Cache()
    order: list[str] = []

    @injectable(cache=cache)
    class Service:
        @post_init
        def init(self) -> None:
            order.append("init")

    def before_service_init(s: Service) -> None:
        order.append("before")

    def after_service_init(s: Service) -> None:
        order.append("after")

    after_init(after_service_init)(Service)
    before_init(before_service_init)(Service)

    inject = Injection(cache)
    inject.require(Service)

    assert order == ["before", "init", "after"]


def test_post_init_called_once() -> None:
    cache = Cache()
    passed = {"count": 0}

    class BaseService:
        @post_init
        def init(self) -> None:
            passed["count"] += 1

    class SubBase1(BaseService):
        pass

    class SubBase2(BaseService):
        pass

    @injectable(cache=cache)
    class Service(SubBase1, SubBase2):
        pass

    inject = Injection(cache)
    inject.require(Service)

    assert passed["count"] == 1
