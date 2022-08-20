from bolinette.core.init import InitFunction


def test_init_func() -> None:
    async def _test_func() -> None:
        pass

    ic = InitFunction(_test_func)

    assert isinstance(ic, InitFunction)
    assert ic.function is _test_func
    assert ic.name == _test_func.__name__
    assert str(ic) == _test_func.__name__


async def test_call_init_func() -> None:
    async def _test_func(d: dict) -> None:
        d["inc"] += 1

    ic = InitFunction(_test_func)
    values = {"inc": 0}

    await ic.function(values)
    assert values["inc"] == 1

    await ic(values)
    assert values["inc"] == 2
