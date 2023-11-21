from typing import Any

import pytest

from bolinette.core import meta
from bolinette.core.exceptions import InternalError
from bolinette.core.metadata import BolinetteMetadata, get_meta_container


class _Meta:
    def __init__(self, value: Any) -> None:
        self._value = value

    @property
    def value(self) -> Any:
        return self._value


def test_set_get_meta() -> None:
    class _TestClass:
        pass

    t = _TestClass()

    _m = _Meta(4)
    meta.set(t, _m)

    assert meta.has(t, _Meta)
    assert not meta.has(_TestClass, _Meta)

    m = meta.get(t, _Meta)

    assert isinstance(m, _Meta)
    assert m is _m
    assert m.value == 4


def test_set_get_meta_class() -> None:
    class _TestClass:
        pass

    _m = _Meta(4)
    meta.set(_TestClass, _m)

    assert meta.has(_TestClass, _Meta)
    assert not meta.has(_TestClass(), _Meta)

    m = meta.get(_TestClass, _Meta)

    assert isinstance(m, _Meta)
    assert m is _m
    assert m.value == 4


def test_set_get_meta_obj_class() -> None:
    class _TestClass:
        pass

    meta.set(_TestClass, _Meta(0))

    t1 = _TestClass()
    t2 = _TestClass()

    meta.set(t1, _Meta(1))
    meta.set(t2, _Meta(2))

    assert meta.get(t1, _Meta) is not meta.get(_TestClass, _Meta)
    assert meta.get(t2, _Meta) is not meta.get(_TestClass, _Meta)
    assert meta.get(type(t1), _Meta) is meta.get(_TestClass, _Meta)
    assert meta.get(type(t2), _Meta) is meta.get(_TestClass, _Meta)

    assert meta.get(type(t1), _Meta).value == 0
    assert meta.get(type(t2), _Meta).value == 0
    assert meta.get(t1, _Meta).value == 1
    assert meta.get(t2, _Meta).value == 2


def test_set_meta_fail_type() -> None:
    class _TestClass:
        pass

    with pytest.raises(TypeError):
        meta.set(_TestClass(), _Meta(0), cls=_Meta(0))  # pyright: ignore

    with pytest.raises(TypeError):
        meta.set(_TestClass(), _TestClass(), cls=_Meta)


def test_get_meta_fail_key() -> None:
    class _TestClass:
        pass

    with pytest.raises(KeyError):
        meta.get(_TestClass(), _Meta)


def test_fail_get_container() -> None:
    class _TestClass:
        pass

    setattr(_TestClass, "__blnt_meta__", 0)

    with pytest.raises(InternalError) as info:
        get_meta_container(_TestClass)

    assert (
        f"Metadata container in {_TestClass} has been overwritten. "
        "Please do not use '__blnt_meta__' as an attribute in any class"
    ) in info.value.message


def test_fail_container_set_item() -> None:
    class _TestClass:
        pass

    _c = BolinetteMetadata()

    with pytest.raises(TypeError):
        _c[_TestClass()] = 0  # pyright: ignore


def test_fail_container_set_item_wrong_type() -> None:
    class _TestClass:
        pass

    _c = BolinetteMetadata()

    with pytest.raises(TypeError):
        _c[_TestClass] = 0


def test_set_get_meta_default() -> None:
    class _TestClass:
        pass

    _m = _Meta(0)
    t1 = _TestClass()

    assert meta.get(t1, _Meta, default=_m) is _m
