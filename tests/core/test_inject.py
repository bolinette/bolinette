from typing import Any, Generic, Optional, TypeVar

import pytest

from bolinette import Cache, GenericMeta, Injection, init_method, injectable, meta, require
from bolinette.exceptions import InjectionError
from bolinette.inject import ArgResolverOptions, _InjectionContext, injection_arg_resolver


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
    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassA, "singleton")
    inject.add(InjectableClassB, "singleton")
    inject.add(InjectableClassC, "singleton")
    inject.add(InjectableClassD, "singleton")

    a = inject.require(InjectableClassA)

    assert a.func() == "a"
    assert a.b.func() == "b"
    assert a.d_attr.func() == "d"
    assert a.d_attr.c.func() == "c"


def test_class_injection_from_cache() -> None:
    cache = Cache()

    injectable(cache=cache)(InjectableClassA)
    injectable(cache=cache)(InjectableClassB)
    injectable(cache=cache)(InjectableClassC)
    injectable(cache=cache)(InjectableClassD)

    inject = Injection(cache, _InjectionContext())

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

    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassA, "singleton")
    inject.add(InjectableClassB, "singleton")
    inject.add(InjectableClassC, "singleton")
    inject.add(InjectableClassD, "singleton")

    inject.call(_test_func)


async def test_inject_call_async() -> None:
    async def _test_func(b: InjectableClassB) -> None:
        assert b.func() == "b"

    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassB, "singleton")

    await inject.call(_test_func)


async def test_fail_injection() -> None:
    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassB, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassC)

    assert f"Type {InjectableClassC} is not a registered type in the injection system" == info.value.message


async def test_fail_injection_generic() -> None:
    _T = TypeVar("_T")

    class _Param:
        pass

    class _Service(Generic[_T]):
        pass

    inject = Injection(Cache(), _InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.require(_Service[_Param])

    assert f"Type {_Service}[({_Param},)] is not a registered type in the injection system" == info.value.message


async def test_fail_subinjection() -> None:
    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassD, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(InjectableClassD)

    assert (
        f"Callable {InjectableClassD}, Parameter 'c', Type {InjectableClassC} is not a registered type in the injection system"
        == info.value.message
    )


async def test_fail_subinjection_generic() -> None:
    _T = TypeVar("_T")

    class _Param:
        pass

    class _SubService(Generic[_T]):
        pass

    class _Service:
        def __init__(self, sub: _SubService[_Param]) -> None:
            pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_Service, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_Service)

    assert (
        f"Callable {_Service}, Parameter 'sub', Type {_SubService}[({_Param},)] is not a registered type in the injection system"
        == info.value.message
    )


def test_fail_call_injection() -> None:
    def _test_func(b: InjectableClassC) -> None:
        assert b.func() == "b"

    inject = Injection(Cache(), _InjectionContext())
    with pytest.raises(InjectionError) as info:
        inject.call(_test_func)

    assert (
        f"Callable {_test_func}, Parameter 'b', Type {InjectableClassC} is not a registered type in the injection system"
        == info.value.message
    )


def test_require_twice() -> None:
    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassB, "singleton")

    b1 = inject.require(InjectableClassB)
    b2 = inject.require(InjectableClassB)

    assert b1 is b2


def test_add_instance_no_singleton() -> None:
    inject = Injection(Cache(), _InjectionContext())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassB, "transcient", instance=b)

    assert f"Injection strategy for {InjectableClassB} must be singleton if an instance is provided" == info.value.message


def test_add_instance_wrong_type() -> None:
    inject = Injection(Cache(), _InjectionContext())

    b = InjectableClassB()

    with pytest.raises(InjectionError) as info:
        inject.add(InjectableClassA, "singleton", instance=b)

    assert f"Object provided must an instance of type {InjectableClassA}" == info.value.message


def test_add_instance() -> None:
    inject = Injection(Cache(), _InjectionContext())

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

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert f"Callable {_TestClass}, Type hint '_Value' could not be resolved" == info.value.message


def test_no_annotation() -> None:
    class _TestClass:
        def __init__(self, _1, _2) -> None:
            pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert f"Callable {_TestClass}, Parameter '_1', Annotation is required" == info.value.message


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

    inject = Injection(Cache(), _InjectionContext())
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


def test_arg_resolve_fail_wilcard() -> None:
    def _test_func(a, *args) -> None:
        pass

    inject = Injection(Cache(), _InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, named_args={"a": "a", "b": "b"})

    assert (
        f"Callable {_test_func}, Positional only parameters and positional wildcards are not allowed"
        == info.value.message
    )


def test_arg_resolve_fail_positional_only() -> None:
    def _test_func(a, /, b) -> None:
        pass

    inject = Injection(Cache(), _InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, named_args={"a": "a", "b": "b"})

    assert (
        f"Callable {_test_func}, Positional only parameters and positional wildcards are not allowed"
        == info.value.message
    )


def test_arg_resolve_fail_too_many_args() -> None:
    def _test_func(a, b) -> None:
        pass

    inject = Injection(Cache(), _InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.call(_test_func, args=["a", "b", "c"])

    assert f"Callable {_test_func}, Expected 2 arguments, 3 given" == info.value.message


def test_arg_resolve() -> None:
    def _test_func(a, b, c: InjectableClassC, d="d", **kwargs) -> None:
        assert a == "a"
        assert b == "b"
        assert c.func() == "c"
        assert d == "d"
        assert kwargs == {"e": "e", "f": "f"}

    inject = Injection(Cache(), _InjectionContext())
    inject.add(InjectableClassC, "singleton")

    inject.call(_test_func, args=["a"], named_args={"b": "b", "e": "e", "f": "f"})


def test_two_injections() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    class _C3:
        def __init__(self, c1: _C1) -> None:
            self.c1 = c1

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "singleton")
    inject.add(_C2, "singleton")
    inject.add(_C3, "singleton")

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

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "transcient")
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

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "scoped")

    with pytest.raises(InjectionError) as info:
        inject.require(_C1)

    assert f"Type {_C1}, Cannot instanciate a scoped service outside of a scoped session" == info.value.message


def test_scoped_injection_fail_no_scope_in_singleton() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "scoped")
    inject.add(_C2, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_C2)

    assert (
        f"Callable {_C2}, Parameter 'c1', Cannot instanciate a scoped service in a non-scoped one" == info.value.message
    )


def test_scoped_injection_fail_no_scope_in_transcient() -> None:
    class _C1:
        pass

    class _C2:
        def __init__(self, c1: _C1) -> None:
            pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "scoped")
    inject.add(_C2, "transcient")

    with pytest.raises(InjectionError) as info:
        inject.require(_C2)

    assert (
        f"Callable {_C2}, Parameter 'c1', Cannot instanciate a scoped service in a non-scoped one" == info.value.message
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

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "transcient")
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
    inject = Injection(Cache(), _InjectionContext())
    sub_inject1 = inject.get_scoped_session()
    sub_inject2 = inject.get_scoped_session()

    assert inject.require(Injection) is inject
    assert sub_inject1.require(Injection) is sub_inject1
    assert sub_inject2.require(Injection) is sub_inject2


def test_require_transcient_service() -> None:
    class _C1:
        pass

    class _C2:
        pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_C1, "transcient")
    inject.add(_C2, "singleton")

    assert inject.require(_C1) is not inject.require(_C1)
    assert inject.require(_C2) is inject.require(_C2)


def test_inject_nullable() -> None:
    class _TestClass:
        def __init__(self, sub: _SubTestClass | None, i: int | None) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None
    assert t.i is None


def test_inject_nullable_bis() -> None:
    class _TestClass:
        def __init__(self, sub: Optional[_SubTestClass]) -> None:
            self.sub = sub

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_inject_with_default() -> None:
    s = _SubTestClass()

    class _TestClass:
        def __init__(self, sub: _SubTestClass = s, i: int = 3) -> None:
            self.sub = sub
            self.i = i

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is s
    assert t.i == 3


def test_inject_no_union() -> None:
    class _TestClass:
        def __init__(self, v: int | bool) -> None:
            self.v = v

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_TestClass)

    assert f"Callable {_TestClass}, Parameter 'v', Type unions are not allowed" == info.value.message


def test_optional_type_literal_right() -> None:
    class _TestClass:
        def __init__(self, sub: "_SubTestClass | None") -> None:
            self.sub = sub

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_optional_type_literal_left() -> None:
    class _TestClass:
        def __init__(self, sub: "None | _SubTestClass") -> None:
            self.sub = sub

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_optional_type_literal_bis() -> None:
    class _TestClass:
        def __init__(self, sub: "Optional[_SubTestClass]") -> None:
            self.sub = sub

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.sub is None


def test_generic_injection() -> None:
    _T = TypeVar("_T")

    class _GenericTest(Generic[_T]):
        pass

    class _ParamClass:
        pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_GenericTest[_ParamClass], "singleton")

    g = inject.require(_GenericTest[_ParamClass])

    assert meta.has(g, GenericMeta)
    assert meta.get(g, GenericMeta).args == (_ParamClass,)


def test_generic_injection_from_cache() -> None:
    _T = TypeVar("_T")

    class _GenericTest(Generic[_T]):
        pass

    class _ParamClass:
        pass

    cache = Cache()

    injectable(cache=cache)(_GenericTest[_ParamClass])

    inject = Injection(cache, _InjectionContext())

    g = inject.require(_GenericTest[_ParamClass])

    assert meta.has(g, GenericMeta)
    assert meta.get(g, GenericMeta).args == (_ParamClass,)


def test_generic_no_direct_injection_literal() -> None:
    _T = TypeVar("_T")

    class _GenericTest(Generic[_T]):
        pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_GenericTest, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_GenericTest["_SubTestClass"])

    assert (
        f"Type {_GenericTest}, Generic parameter ForwardRef('_SubTestClass'), "
        "literal type hints are not allowed in direct require calls" == info.value.message
    )


def test_generic_sub_injection() -> None:
    _T = TypeVar("_T")

    class _GenericTest(Generic[_T]):
        pass

    class _ParamClass:
        pass

    class _TestClass:
        def __init__(self, g: _GenericTest[_ParamClass]) -> None:
            self.g = g

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_GenericTest[_ParamClass], "singleton")
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert meta.has(t.g, GenericMeta)
    assert meta.get(t.g, GenericMeta).args == (_ParamClass,)


def test_generic_sub_injection_literal() -> None:
    _T = TypeVar("_T")

    class _GenericTest(Generic[_T]):
        pass

    class _TestClass:
        def __init__(self, g: _GenericTest["_SubTestClass"]) -> None:
            self.g = g

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_GenericTest[_SubTestClass], "singleton")
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert meta.has(t.g, GenericMeta)
    assert meta.get(t.g, GenericMeta).args == (_SubTestClass,)


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

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_ParamClass, "singleton")
    inject.add(_TestClass, "singleton")

    t = inject.require(_TestClass)

    assert t.param.v == 1


def test_fail_immediate_instanciate() -> None:
    class _TestClass:
        pass

    inject = Injection(Cache(), _InjectionContext())

    with pytest.raises(InjectionError) as info:
        inject.add(
            _TestClass,
            "singleton",
            instance=_TestClass(),
            instanciate=True,
        )

    assert f"Cannot instanciate {_TestClass} if an instance is provided" == info.value.message


def test_register_with_super_type() -> None:
    _T = TypeVar("_T")

    class _Service(Generic[_T]):
        pass

    class _User:
        pass

    class _Role:
        pass

    class _UserService(_Service[_User]):
        pass

    class _RoleService(_Service[_Role]):
        pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_UserService, "singleton", super_cls=_Service[_User])
    inject.add(_RoleService, "singleton", super_cls=_Service[_Role])

    us = inject.require(_Service[_User])
    assert isinstance(us, _UserService)

    rs = inject.require(_Service[_Role])
    assert isinstance(rs, _RoleService)


def test_register_with_super_type_complete() -> None:
    _T = TypeVar("_T")

    class _Service(Generic[_T]):
        pass

    class _User:
        pass

    class _Role:
        pass

    class _UserService(_Service[_User]):
        pass

    class _RoleService(_Service[_Role]):
        pass

    inject = Injection(Cache(), _InjectionContext())
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
    _T = TypeVar("_T")

    class _ServiceA:
        pass

    class _ServiceB:
        pass

    class _Logger(Generic[_T]):
        pass

    class _LoggerA(_Logger[_ServiceA]):
        pass

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_Logger, "singleton", match_all=True)
    inject.add(_LoggerA, "singleton", super_cls=_Logger[_ServiceA])

    _loggerA = inject.require(_Logger[_ServiceA])
    _loggerB = inject.require(_Logger[_ServiceB])

    assert isinstance(_loggerA, _Logger)
    assert isinstance(_loggerA, _LoggerA)
    assert meta.get(_loggerA, GenericMeta).args == (_ServiceA,)

    assert isinstance(_loggerB, _Logger)
    assert not isinstance(_loggerB, _LoggerA)
    assert meta.get(_loggerB, GenericMeta).args == (_ServiceB,)


def test_require_from_typevar() -> None:
    class _Resource:
        pass

    class _SpecificResource(_Resource):
        pass

    _TS = TypeVar("_TS", bound=_Resource)

    class _Service(Generic[_TS]):
        pass

    class _SpecificService(_Service[_SpecificResource]):
        pass

    _TC = TypeVar("_TC", bound=_Resource)

    class _Controller(Generic[_TC]):
        def __init__(self, sub: _Service[_TC]) -> None:
            self.sub = sub

    inject = Injection(Cache(), _InjectionContext())
    inject.add(_Service[_Resource], "singleton")
    inject.add(_SpecificService, "singleton", super_cls=_Service[_SpecificResource])

    inject.add(_Controller[_Resource], "singleton")
    inject.add(_Controller[_SpecificResource], "singleton")

    ctrl = inject.require(_Controller[_Resource])
    assert isinstance(ctrl.sub, _Service)

    ctrl2 = inject.require(_Controller[_SpecificResource])
    assert isinstance(ctrl2.sub, _SpecificService)


def test_fail_require_from_typevar_non_generic_parent() -> None:
    class _Entity:
        pass

    _T = TypeVar("_T", bound=_Entity)

    class _Service(Generic[_T]):
        pass

    class _Controller:
        def __init__(self, s: _Service[_T]) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_Service[_Entity], "singleton")
    inject.add(_Controller, "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_Controller)

    assert f"Type {_Controller}, Parameter 's', TypeVar cannot be used from a non generic class" == info.value.message


def test_fail_require_from_typevar_different_names() -> None:
    class _Entity1:
        pass

    class _Entity2:
        pass

    _T1 = TypeVar("_T1", bound=_Entity1)
    _T2 = TypeVar("_T2", bound=_Entity2)

    class _Service(Generic[_T1]):
        pass

    class _Controller(Generic[_T2]):
        def __init__(self, s: _Service[_T1]) -> None:
            pass

    inject = Injection(Cache())
    inject.add(_Service[_Entity1], "singleton")
    inject.add(_Controller[_Entity2], "singleton")

    with pytest.raises(InjectionError) as info:
        inject.require(_Controller[_Entity2])

    assert (
        f"Type {_Controller}, Parameter 's', TypeVar ~_T1 could not be found in calling declaration"
        == info.value.message
    )


def test_arg_resolver() -> None:
    cache = Cache()

    order = []

    class _Service:
        pass

    class _Controller:
        def __init__(self, s: _Service) -> None:
            self.s = s

    _s = _Service()

    @injection_arg_resolver(priority=2, cache=cache)
    class _Resolver2:
        def supports(self, options: ArgResolverOptions):
            order.append(3)
            return True

        def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
            order.append(4)
            return (options.name, _s)

    @injection_arg_resolver(priority=1, cache=cache)
    class _Resolver1:
        def supports(self, options: ArgResolverOptions):
            order.append(1)
            return False

        def resolve(self, options: ArgResolverOptions) -> tuple[str, Any]:
            order.append(2)
            return ("", 0)

    inject = Injection(cache)
    inject.add(_Controller, "singleton")

    ctrl = inject.require(_Controller)

    assert order == [1, 3, 4]
    assert ctrl.s is _s
