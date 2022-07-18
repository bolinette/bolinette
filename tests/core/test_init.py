import pytest
from bolinette.core import InitFunction
from bolinette.core.exceptions import InitError


def test_init_func_non_async() -> None:
    def _test_func() -> None:
        pass

    with pytest.raises(InitError) as info:
        InitFunction(_test_func)

    assert (
        f"'{_test_func}' must be an async function to be an init function"
        in info.value.message
    )


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
