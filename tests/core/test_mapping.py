import pytest

from bolinette.exceptions import InitError
from bolinette.mapping import mapFrom


def test_fail_mapping_prop_no_return_type() -> None:
    with pytest.raises(InitError) as info:

        class _:
            @mapFrom
            def test(self):
                pass

    assert "Property 'test' must specify a return type hint when decorated by @mapFrom" == info.value.message


def test_fail_call_prop_before_mapping() -> None:
    class _TestMapping:
        @mapFrom
        def attr(self) -> str:
            return str(self)

    _test = _TestMapping()

    with pytest.raises(AttributeError) as info:
        _test.attr

    assert "'_TestMapping' object has no attribute 'attr'" == str(info.value)
