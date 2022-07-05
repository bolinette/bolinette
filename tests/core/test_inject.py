from bolinette.core import Cache, Injection


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
    def __init__(self, b: InjectableClassB, d_param: InjectableClassD) -> None:
        self.b = b
        self.d_attr = d_param

    def func(self) -> str:
        return "a"


async def test_class_injection():
    cache = Cache()
    cache.add_type(
        InjectableClassA, InjectableClassB, InjectableClassC, InjectableClassD
    )

    inject = Injection(cache=cache)
    a = inject.require(InjectableClassA)

    assert a.func() == "a"
    assert a.b.func() == "b"
    assert a.d_attr.func() == "d"
    assert a.d_attr.c.func() == "c"
